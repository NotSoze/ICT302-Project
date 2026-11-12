"""PDF output regression test: this used to test .html, but the report is PDF."""
import tempfile
from pathlib import Path

from core.report_generator import generate_pdf_report


def test_report_generator_standalone():
    mock = {
        'ok': True,
        'document': {'document_id': 'synthetic-test', 'rsid_root': None, 'metadata': {}},
        'integrity': {'original_sha256': '0' * 64, 'working_copy_verified': True},
        'metrics': {'total_word_count': 2, 'revision_count': None, 'unique_rsid_count': 0},
        'top_sessions': [],
        'paragraphs': [{'text': 'Hello world', 'word_count': 2, 'runs': [{'text': 'Hello world', 'rsidR': None}]}],
    }
    with tempfile.TemporaryDirectory() as folder:
        destination = Path(folder) / 'forensic-report.pdf'
        saved_path = generate_pdf_report(mock, destination)
        assert saved_path.read_bytes().startswith(b'%PDF-')
        assert saved_path.stat().st_size > 500
