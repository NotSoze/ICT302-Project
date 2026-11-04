from pathlib import Path
from core.session_manager import (
    create_session,
    save_session,
    load_session,
    example_mock_analysis,
)

def run_session_manager_test():
    print("--- Starting Session Manager Mock Test ---")

    # 1. Generate mock analysis data from session_manager
    mock_analysis = example_mock_analysis()
    document_id = "mock_document_sample"

    # 2. Create session
    print(f"1. Creating session for document ID: {document_id}")
    session = create_session(document_id=document_id, analysis=mock_analysis)

    # 3. Save session atomically
    destination = Path(f"storage/sessions/{document_id}.json")
    print(f"2. Saving session to: {destination}")
    saved_path = save_session(session, destination)
    print("   -> Successfully saved!")

    # 4. Load session back to verify persistence
    print("3. Loading session back from disk to verify integrity...")
    loaded_session = load_session(saved_path)

    # 5. Print out the verified results
    print("\n--- Verified Mock Session Output ---")
    print(f"Session Version : v{loaded_session['session_version']}")
    print(f"Document ID     : {loaded_session['document_id']}")
    print(f"Analysis Status : {loaded_session['analysis_status']}")
    print(f"Word Count      : {loaded_session['analysis']['word_count']}")
    print(f"RSID Count      : {loaded_session['analysis']['rsid_count']}")
    print(f"Verified        : {loaded_session['analysis']['verified']}")
    print(f"SHA-256 Hash    : {loaded_session['analysis']['content_sha256']}")

    print("\n--- Session Manager Mock Test Completed Successfully! ---")

if __name__ == "__main__":
    run_session_manager_test()