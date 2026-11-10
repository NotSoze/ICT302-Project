from pathlib import Path
from core.report_generator import generate_html_report

def test_report_generator_standalone():
    print("--- Starting Standalone Report Generator Test ---")

    # Mock analysis result containing sample metrics and metadata
    mock_analysis_result = {
        "ok": True,
        "document": {
            "document_id": "sample_test_document",
            "rsid_root": "ABC12345",
            "metadata": {
                "creation_date": "2026-10-31T10:00:00Z",
                "modified_date": "2026-10-31T11:30:00Z"
            }
        },
        "integrity": {
            "original_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "working_copy_verified": True
        },
        "metrics": {
            "revision_count": 5,
            "total_word_count": 1250,
            "unique_rsid_count": 2,
            "word_to_revision_ratio": 250.0,
            "unique_rsid_to_revision_ratio": 0.4
        },
        "top_sessions": [
            {
                "rsid": "ABC12345",
                "word_count": 950,
                "session_type": "Primary"
            },
            {
                "rsid": "DEF67890",
                "word_count": 300,
                "session_type": "Secondary/Other"
            }
        ]
    }

    # Define output destination
    destination = Path("storage/temp_workspace/standalone_test_report.html")
    
    print(f"Generating HTML report at: {destination}")
    saved_path = generate_html_report(mock_analysis_result, destination)
    
    print(f" -> Successfully generated standalone report: {saved_path}")
    print("--- Standalone Report Generator Test Completed Successfully! ---")

if __name__ == "__main__":
    test_report_generator_standalone()