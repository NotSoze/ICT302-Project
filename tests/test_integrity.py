# CHATGPT GENERATED TEST

"""Tests for CopyQ's evidence-integrity module (Python standard library only)."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from core.integrity import (
    create_verified_copy,
    sha256_file,
    verify_working_copy,
)


class TestIntegrity(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.original = self.folder / "original.docx"
        self.working_copy = self.folder / "working" / "copy.docx"
        # These are test bytes, not a real Word document. Hashing needs only bytes.
        self.content = b"CopyQ test evidence - no real student documents."
        self.original.write_bytes(self.content)

    def test_sha256_matches_reference(self):
        self.assertEqual(
            sha256_file(self.original),
            hashlib.sha256(self.content).hexdigest(),
        )

    def test_verified_copy_has_matching_hash_and_preserves_original(self):
        result = create_verified_copy(self.original, self.working_copy)
        self.assertTrue(result["verified_initial"])
        self.assertEqual(result["original_hash"], result["copy_hash_initial"])
        self.assertEqual(self.working_copy.read_bytes(), self.content)
        self.assertEqual(self.original.read_bytes(), self.content)

    def test_unchanged_working_copy_passes_verification(self):
        result = create_verified_copy(self.original, self.working_copy)
        self.assertTrue(
            verify_working_copy(self.working_copy, result["copy_hash_initial"])
        )

    def test_modified_working_copy_fails_verification(self):
        result = create_verified_copy(self.original, self.working_copy)
        self.working_copy.write_bytes(b"Tampered contents")
        self.assertFalse(
            verify_working_copy(self.working_copy, result["copy_hash_initial"])
        )

    def test_missing_source_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            create_verified_copy(self.folder / "missing.docx", self.working_copy)

    def test_copying_onto_itself_is_rejected(self):
        with self.assertRaises(ValueError):
            create_verified_copy(self.original, self.original)

    def test_existing_destination_is_not_overwritten(self):
        self.working_copy.parent.mkdir(parents=True)
        self.working_copy.write_bytes(b"Existing data")
        with self.assertRaises(FileExistsError):
            create_verified_copy(self.original, self.working_copy)
        self.assertEqual(self.working_copy.read_bytes(), b"Existing data")


if __name__ == "__main__":
    unittest.main()
