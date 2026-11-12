# CopyQ — local DOCX forensic analysis (development build)

CopyQ inspects locally supplied `.docx` files, preserves and verifies a working copy, displays available Word metadata and RSID-associated text, saves analysis sessions, and exports a PDF. It does **not** identify authors, prove pasting, reconstruct exact writing chronology, or determine misconduct.

## Run on Windows (VS Code terminal / PowerShell)

1. Install Python 3.12, Git and VS Code (if needed).
2. Open the **project root** (the folder containing `main.py`) in VS Code.
3. In its terminal:

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
```

4. Select one **`.docx`**. Analysis starts automatically. Use the summary for metadata, observations, recorded dates, and the **document-order** paragraph player. Select a paragraph to see RSID details or **Text Statistics**.
5. Select **Export Full Analysis** to choose a PDF destination.

To run automated tests (install `pytest` separately if needed):

```powershell
py -3.12 -m pip install pytest
py -3.12 -m pytest -q
```

All data is handled locally. Do **not** commit actual student documents, analysis sessions, temp working copies, or verification logs to GitHub.

## What RSIDs do and don't tell you

- `rsidR`: paragraph addition context; `rsidRDefault`: default for runs without their own RSID; text runs may have their own `rsidR`.
- The **Root** group matches `w:rsidRoot`. **Other** identifies another usable RSID. Neither identifies an author.
- `00000000`, absent, and malformed RSIDs are treated as **unavailable**. Missing revision counts are not silently replaced with 1.
- When a word spans multiple XML runs, CopyQ counts it **once** and attributes it to the run containing the most characters (ties to the first). This is a stated approximation.
- The player steps through **current document order**, not established editing chronology. The recorded-date view shows document-property dates only when present.
- The review indicator for a large RSID-associated group uses a *non-validated descriptive* threshold (60% of words, documents of at least 100 words). It does **not** prove a paste event.

## Notes for the developer / demonstrator

- This ZIP is a revised **local code snapshot**; it does not modify the team's original GitHub repository or create a PR.
- Source mode stores local sessions/verification logs/workspaces under `storage/`; packaged/frozen mode uses `%LOCALAPPDATA%\\CopyQ\\storage`.
- The GUI runs using `pywebview`/PySide6. The offline test environment could run backend/JavaScript tests, **not** a complete Windows Qt session. Validate once on the demonstration laptop.
- `reportlab` is used for actual PDF output instead of the previous HTML report or an untested HTML→PDF conversion.
- No installation executable is included. A PyInstaller build still needs Windows verification and appropriate `ui/` asset bundling.
- Do not use Google Docs exports as the only demonstration files: some contain all-zero RSIDs and no core document properties. Use a real Word-created `.docx` with meaningful RSIDs to show grouping; use Google Docs export to demonstrate the unavailable-data fallback.

See `IMPLEMENTATION_NOTES.md` for FR cross-check and known limitations.
