"""Local JSON session storage for CopyQ analyst results.

This module deliberately uses only Python's standard library.  It is designed
to be called by CopyQ's local desktop file-parsing engine; it never uploads a
document or its analysis result.
"""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


CURRENT_SESSION_VERSION = 2


class SessionError(Exception):
    """Base class for session storage errors that the user interface can show."""


class SessionNotFoundError(SessionError):
    """Raised when the requested saved session does not exist."""


class InvalidSessionError(SessionError):
    """Raised when a session file is not valid JSON or has an unsafe structure."""


def default_session_directory(app_name: str = "CopyQ") -> Path:
    """Return CopyQ's per-user writable directory without creating it.

    ``LOCALAPPDATA`` is preferred on Windows.  The fallback keeps local tests
    usable on other operating systems without putting files beside source code.
    """
    base_directory = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local"))
    return base_directory / app_name / "sessions"


def sha256_text(text: str) -> str:
    """Create the SHA-256 hash used by early mock analysis data.

    A hash lets tests confirm that content has not changed while avoiding the
    need to save full document text in a session.  Real parser metadata can be
    added later through the ``metadata`` field.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_session(document_id: str, analysis: dict[str, Any]) -> dict[str, Any]:
    """Build a new in-memory session in the current CopyQ JSON format.

    ``analysis`` may contain partial results.  It is copied so a caller cannot
    accidentally alter the in-memory session after it has been saved.
    """
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document_id must be a non-empty string")
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be a JSON-object-like dictionary")

    timestamp = _utc_timestamp()
    return {
        "session_version": CURRENT_SESSION_VERSION,
        "document_id": document_id,
        "created_at": timestamp,
        "updated_at": timestamp,
        "analysis_status": "partial",
        "analysis": deepcopy(analysis),
    }


def save_session(session: dict[str, Any], destination: str | Path) -> Path:
    """Validate and atomically save one session as readable, indented JSON.

    Atomic replacement prevents a power loss or interrupted analysis from
    replacing an intact session with a half-written JSON file.
    """
    normalised = _normalise_session(session)
    normalised["updated_at"] = _utc_timestamp()
    file_path = Path(destination)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".tmp", dir=file_path.parent,
            delete=False,
        ) as temporary_file:
            json.dump(normalised, temporary_file, indent=2, ensure_ascii=False)
            temporary_file.write("\n")
            temporary_name = temporary_file.name
        Path(temporary_name).replace(file_path)
    except OSError as error:
        raise SessionError(f"Could not save session '{file_path}': {error}") from error

    return file_path


def load_session(source: str | Path) -> dict[str, Any]:
    """Load and migrate a current or older CopyQ JSON session file.

    Version 1 files did not contain ``session_version`` or timestamps.  They
    are accepted and upgraded in memory, so users do not lose old sessions.
    """
    file_path = Path(source)
    if not file_path.is_file():
        raise SessionNotFoundError(f"Session file was not found: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as session_file:
            stored_session = json.load(session_file)
    except json.JSONDecodeError as error:
        raise InvalidSessionError(f"Session file is not valid JSON: {file_path}") from error
    except OSError as error:
        raise SessionError(f"Could not read session '{file_path}': {error}") from error

    return _normalise_session(stored_session)


def sessions_match(expected: dict[str, Any], reloaded: dict[str, Any]) -> bool:
    """Return whether two sessions hold the same meaningful stored information.

    ``updated_at`` is ignored because each save intentionally refreshes it.
    """
    expected_copy = _normalise_session(expected)
    reloaded_copy = _normalise_session(reloaded)
    expected_copy.pop("updated_at", None)
    reloaded_copy.pop("updated_at", None)
    return expected_copy == reloaded_copy


def example_mock_analysis() -> dict[str, Any]:
    """Return safe test data until the client supplies real document metadata."""
    mock_text = "This is CopyQ mock document content for session-storage testing."
    return {
        # Appendix B naming: these keys match the currently agreed mock result.
        # Add or rename a key only after recording the Appendix B change here.
        "word_count": 500,
        "rsid_count": 3,
        "verified": True,
        "content_sha256": sha256_text(mock_text),
        # Client metadata has not yet been supplied.  Keep this field present so
        # the parser can later insert OOXML metadata without changing the format.
        "metadata": {},
    }


def _normalise_session(raw_session: Any) -> dict[str, Any]:
    """Validate session data and upgrade known old formats to version 2."""
    if not isinstance(raw_session, dict):
        raise InvalidSessionError("A session must be a JSON object")

    session = deepcopy(raw_session)
    version = session.get("session_version", 1)
    if version == 1:
        session = _migrate_version_1(session)
    elif version != CURRENT_SESSION_VERSION:
        raise InvalidSessionError(f"Unsupported session version: {version!r}")

    if not isinstance(session.get("document_id"), str) or not session["document_id"].strip():
        raise InvalidSessionError("Session document_id must be a non-empty string")
    if not isinstance(session.get("analysis"), dict):
        raise InvalidSessionError("Session analysis must be a JSON object")
    if session.get("analysis_status") not in {"partial", "complete", "failed"}:
        raise InvalidSessionError("Session analysis_status must be partial, complete, or failed")
    return session


def _migrate_version_1(old_session: dict[str, Any]) -> dict[str, Any]:
    """Convert the original flat mock-result format into the version 2 layout."""
    document_id = old_session.get("document_id")
    if not isinstance(document_id, str) or not document_id.strip():
        raise InvalidSessionError("Old session is missing a valid document_id")

    legacy_analysis = {
        key: value for key, value in old_session.items() if key != "document_id"
    }
    timestamp = _utc_timestamp()
    return {
        "session_version": CURRENT_SESSION_VERSION,
        "document_id": document_id,
        "created_at": old_session.get("created_at", timestamp),
        "updated_at": old_session.get("updated_at", timestamp),
        "analysis_status": old_session.get("analysis_status", "complete"),
        "analysis": legacy_analysis,
    }


def _utc_timestamp() -> str:
    """Return a portable UTC ISO-8601 timestamp for JSON storage."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")