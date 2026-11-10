import zipfile
from pathlib import Path

ZIP_MAGIC = b"PK\x03\x04"
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_UNCOMPRESSED = 500 * 1024 * 1024
MAX_RATIO = 100
REQUIRED_PARTS = ["[Content_Types].xml", "_rels/.rels", "word/document.xml"]
DOCX_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
DOCM_MAIN = "application/vnd.ms-word.document.macroEnabled.main+xml"
DOTX_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"


def new_result(path):
    return {
        "path": str(path),
        "valid": False,
        "file_type": None,
        "needs_conversion": False,
        "size": 0,
        "errors": [],
        "warnings": [],
    }


def validate_file(path):
    p = Path(path)
    result = new_result(p)

    if not p.exists():
        result["errors"].append("file does not exist")
        return result
    if not p.is_file():
        result["errors"].append("path is not a file")
        return result

    ext = p.suffix.lower()
    if ext not in (".docx", ".doc"):
        result["errors"].append("unsupported file extension: " + ext)
        return result

    result["size"] = p.stat().st_size
    if result["size"] == 0:
        result["errors"].append("file is empty")
        return result
    if result["size"] > MAX_FILE_SIZE:
        result["errors"].append("file is larger than the 50MB limit")
        return result

    with open(p, "rb") as f:
        header = f.read(8)

    if header.startswith(ZIP_MAGIC):
        result["file_type"] = "docx"
        if ext == ".doc":
            result["warnings"].append("file has a .doc extension but is really a .docx")
        check_docx(p, result)
    elif header == OLE_MAGIC:
        result["file_type"] = "doc"
        result["needs_conversion"] = True
        if ext == ".docx":
            result["warnings"].append("file has a .docx extension but is a legacy .doc or is password protected")
    else:
        result["errors"].append("file header does not match a Word document")

    result["valid"] = len(result["errors"]) == 0
    return result


def check_docx(p, result):
    try:
        zf = zipfile.ZipFile(p)
    except zipfile.BadZipFile:
        result["errors"].append("corrupted zip structure")
        return

    with zf:
        names = zf.namelist()
        total = 0
        for info in zf.infolist():
            parts = info.filename.replace("\\", "/").split("/")
            if info.filename.startswith(("/", "\\")) or ".." in parts or ":" in info.filename:
                result["errors"].append("unsafe path in archive: " + info.filename)
            if info.flag_bits & 0x1:
                result["errors"].append("encrypted entry in archive: " + info.filename)
            total += info.file_size
            if info.file_size > 1024 * 1024 and info.compress_size > 0:
                if info.file_size / info.compress_size > MAX_RATIO:
                    result["errors"].append("suspicious compression ratio: " + info.filename)

        if total > MAX_UNCOMPRESSED:
            result["errors"].append("uncompressed size too large, possible zip bomb")
        if result["errors"]:
            return

        for part in REQUIRED_PARTS:
            if part not in names:
                result["errors"].append("missing required part: " + part)
        if result["errors"]:
            return

        bad = zf.testzip()
        if bad is not None:
            result["errors"].append("crc check failed on: " + bad)
            return

        for name in names:
            if name.endswith((".xml", ".rels")):
                if b"<!DOCTYPE" in zf.read(name):
                    result["errors"].append("DTD found in " + name + ", not allowed in a docx")
        if result["errors"]:
            return

        content_types = zf.read("[Content_Types].xml").decode("utf-8", errors="replace")
        if DOCM_MAIN in content_types:
            result["warnings"].append("document is macro-enabled")
        elif DOTX_MAIN in content_types:
            result["warnings"].append("document is a template")
        elif DOCX_MAIN not in content_types:
            result["errors"].append("main document content type not found")

        if "word/vbaProject.bin" in names:
            result["warnings"].append("document contains a macro project")