from pathlib import Path
from core.validation import validate_file
from core.integrity import create_verified_copy, sha256_file, verify_working_copy
from core.verification_log import Event


def handle_upload(source_path: str | Path, workspace_dir: str | Path = "storage/temp_workspace", log=None) -> tuple[bool, str, dict]:
    """
    Handles forensic ingestion of a Word document:
    1. Validates file header, size, structure, and extension.
    2. Immediately rejects legacy .doc files with a re-upload prompt (no automatic conversion).
    3. Logs FILE_SELECTED and validation events if a VerificationLog is provided.
    4. Copies the file to the isolated temp_workspace, calculates hashes, and logs integrity events.
    """
    src = Path(source_path)
    workspace = Path(workspace_dir)
    
    # 1. Run Validation
    check = validate_file(src)
    
    # Log file selection & validation results if verification log is available
    if log is not None:
        log.write(Event.FILE_SELECTED, file_name=src.name)
        if check["valid"]:
            log.write(Event.VALIDATION_PASSED, file_name=src.name, details={"file_type": check["file_type"]})
        else:
            log.write(Event.VALIDATION_FAILED, file_name=src.name, details={"errors": check["errors"]})

    if not check["valid"]:
        return False, "; ".join(check["errors"]), check
        
    # 2. Strict Gatekeeper for Legacy .doc (No automatic conversion)
    if check["needs_conversion"]:
        msg = "Legacy .doc files are not supported. Please open the file in Word and save it as .docx, then upload again."
        return False, msg, check

    # 3. Establish Isolated Working Copy Path
    dest = workspace / src.name
    # Handle filename collisions in workspace gracefully
    if dest.exists():
        dest = workspace / f"{src.stem}_{sha256_file(src)[:8]}{src.suffix}"

    try:
        # 4. Create Verified Working Copy & Hash
        if log is not None:
            log.write(Event.CONVERSION_STARTED, file_name=src.name, details={"note": "Bypassing conversion; direct .docx ingestion."})
            log.write(Event.CONVERSION_DONE, file_name=src.name)

        # Execute forensic copy and initial verification via integrity module
        integrity_result = create_verified_copy(src, dest)
        orig_hash = integrity_result["original_hash"]
        copy_hash = integrity_result["copy_hash_initial"]

        if log is not None:
            log.write(Event.ORIGINAL_HASHED, file_name=src.name, sha256=orig_hash)
            log.write(Event.WORKING_COPY_CREATED, file_name=dest.name, sha256=copy_hash, details={"destination": str(dest)})

        # 5. Cryptographic Comparison & Verification Logging
        if orig_hash == copy_hash:
            if log is not None:
                log.write(Event.HASH_MATCH, file_name=dest.name, sha256=copy_hash, details={"status": "Working copy hash matches original byte-for-byte."})
        else:
            if log is not None:
                log.write(Event.HASH_MISMATCH, file_name=dest.name, sha256=copy_hash, details={"error": "Hash mismatch between original and working copy."})
            return False, "Cryptographic integrity violation: Working copy hash does not match original file.", check

    except Exception as e:
        if log is not None:
            log.write(Event.CONVERSION_FAILED, file_name=src.name, details={"error": str(e)})
        return False, f"Failed to establish secure working copy: {str(e)}", check

    # Attach workflow paths to check dictionary for downstream modules
    check["original_path"] = str(src.resolve())
    check["working_path"] = str(dest.resolve())
    check["sha256"] = orig_hash

    return True, "ok", check