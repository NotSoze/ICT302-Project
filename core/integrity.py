# IMPORTS
from pathlib import Path
import hashlib
import shutil

def sha256_file(file_path: str | Path) -> str:
# {
    """
    @brief Calculate a file's SHA-256 fingerprint
    """
    
    digest = hashlib.sha256()

    with open(file_path, "rb") as file:
    # {
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    # }

    return digest.hexdigest()
# }

def create_verified_copy(source: str | Path, destination: str | Path) -> dict:
# {    
    """
    @brief Create a working copy and check that it matches the original
    """

    source      = Path(source)
    destination = Path(destination)

        # if original file doesnt exist
    if not source.is_file():
        raise FileNotFoundError(source)

        # if original and destination are same
    if source.resolve() == destination.resolve():
        raise ValueError("Source and destination are identical")

        # if destination already exists
    if destination.exists():
        raise FileExistsError(destination)

    original_hash = sha256_file(source)

    destination.parent.mkdir(parents = True, exist_ok = True)

    shutil.copy2(source, destination)

    copy_hash = sha256_file(destination)

    if original_hash != copy_hash:
        raise ValueError("Working copy integrity check failed")

    return {
        "original_hash": original_hash,
        "copy_hash_initial": copy_hash,
        "verified_initial": True
    }
# }

    
def verify_working_copy(file_path: str | Path, expected_hash: str) -> bool:
# {    
    """
    Check whether that working copy has changed since its initial verification
    """
    return sha256_file(file_path) == expected_hash
# }