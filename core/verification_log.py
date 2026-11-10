import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


class Event:
    FILE_SELECTED = "FILE_SELECTED"
    VALIDATION_PASSED = "VALIDATION_PASSED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    ORIGINAL_HASHED = "ORIGINAL_HASHED"
    WORKING_COPY_CREATED = "WORKING_COPY_CREATED"
    HASH_MATCH = "HASH_MATCH"
    HASH_MISMATCH = "HASH_MISMATCH"
    CONVERSION_STARTED = "CONVERSION_STARTED"
    CONVERSION_DONE = "CONVERSION_DONE"
    CONVERSION_FAILED = "CONVERSION_FAILED"
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    ANALYSIS_DONE = "ANALYSIS_DONE"
    REVERIFY_MATCH = "REVERIFY_MATCH"
    REVERIFY_MISMATCH = "REVERIFY_MISMATCH"


class LogIntegrityError(Exception):
    pass


def hash_entry(entry):
    data = {k: v for k, v in entry.items() if k != "entry_hash"}
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_log(path):
    prev = GENESIS
    count = 0
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return {"ok": False, "count": count, "last_hash": prev, "error": "line " + str(line_no) + " is not valid json"}
            if entry.get("seq") != count + 1:
                return {"ok": False, "count": count, "last_hash": prev, "error": "sequence break at line " + str(line_no)}
            if entry.get("prev_hash") != prev:
                return {"ok": False, "count": count, "last_hash": prev, "error": "chain broken at line " + str(line_no)}
            if hash_entry(entry) != entry.get("entry_hash"):
                return {"ok": False, "count": count, "last_hash": prev, "error": "entry changed at line " + str(line_no)}
            prev = entry["entry_hash"]
            count += 1
    return {"ok": True, "count": count, "last_hash": prev, "error": None}


class VerificationLog:
    def __init__(self, log_path):
        self.path = Path(log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            check = verify_log(self.path)
            if not check["ok"]:
                raise LogIntegrityError(check["error"])
            self.seq = check["count"]
            self.last_hash = check["last_hash"]
        else:
            self.seq = 0
            self.last_hash = GENESIS

    def write(self, event, file_name=None, sha256=None, details=None):
        entry = {
            "seq": self.seq + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "file": file_name,
            "sha256": sha256,
            "details": details or {},
            "prev_hash": self.last_hash,
        }
        entry["entry_hash"] = hash_entry(entry)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self.seq = entry["seq"]
        self.last_hash = entry["entry_hash"]
        return entry

    def entries(self):
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def verify(self):
        if not self.path.exists():
            return {"ok": True, "count": 0, "last_hash": GENESIS, "error": None}
        return verify_log(self.path)