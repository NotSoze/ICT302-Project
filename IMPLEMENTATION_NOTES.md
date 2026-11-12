# CopyQ — R&A alignment and pending acceptance checks

This is an internal development handover, **not** a substitute for the submitted R&A. Recorded client decision (7 Nov 2026): restrict the current release to `.docx` input; legacy `.doc` conversion is rejected.

## Functional requirements cross-check

| R&A item | Current state (this ZIP) | Demo / further verification |
|---|---|---|
| FR-1 Input + working copy | `.docx` accepted and verified working copy created; `.doc` rejected by agreement | Inspect source hash preservation |
| FR-2 Hash verification | SHA-256 plus chain-verified local verification logs | Use integrity unit tests |
| FR-3 OOXML extraction | `document.xml`, optional `settings.xml`, `core.xml`, `app.xml` | Test a corrupted DOCX |
| FR-4 RSID extraction / text mapping | Paragraph/default/run RSIDs and text; split-word allocation approximation | Use Word-saved file; review hard cases |
| FR-5 Metadata/statistics | Creator, modifier, dates, optional app info, revision, page/time, ratios, counts | Validate optional metadata fields |
| FR-6 Colour coding / accessibility | Meaningful RSID groups receive colour + numerical run labels | Check multiple colours and contrast |
| FR-7 Document player | Recorded date view and interactive current-document-order paragraph player; **not** chronological edit reconstruction | The original time-based construction requirement is only **partially met** |
| FR-8 Indicators | Descriptive large-group review note (>=60% and >=100 words) + missing-data notices; no misconduct verdict | Threshold is a UI heuristic, not empirically validated |
| FR-9 Save/reopen | JSON analysis sessions | Verify same result after reopen |
| FR-10 PDF export | Local ReportLab PDF; metadata, metrics, observations, RSID-group table, coloured-run document overview | Windows export dialog still needs manual demo test |
| FR-11 One document per instance | One analysis shown at a time; multiple instances not yet stress-tested | Test concurrent launch if time |
| FR-12 Input/error handling | Unsupported, invalid, corrupted, encrypted/legacy inputs handled with messages | Password unlock is not implemented; unsupported protected files are rejected |
| FR-13 Local LLM style analysis | Not implemented; stretch only | No change needed for MVP |

## Required R&A amendments after client approval

1. **Scope `.docx`-only:** Executive Summary (p.4), FR-1, FR-3 discussion, NFR-4, MVP Appendix D item 4, and Context Diagram on p.18. Modify any mention of `.doc` acceptance and the automatic conversion path. Record the Nov 7 client approval in the change log rather than silently editing historical version 0.
2. **FR-7 timeline:** distinguish recorded creation/modification metadata dates from a **document-order player**; do not promise verified chronological writing-session reconstruction from RSIDs. The latter remains a limitation or scope discussion with Cole.
3. **FR-4/5/8:** clearly state that missing/all-zero RSIDs and missing revision counts yield **unavailable** results. Describe word attribution across split text runs as an approximation. Explain descriptive review rules and avoid unwarranted misconduct interpretations.
4. **FR-10:** PDF exported report now contains document summary, group statistics and current-text visual overview; verify visual parity with the GUI and list any limitations. It does not contain a playable animation (not feasible in a static PDF).
5. **NFR-1 and MVP item 15:** there is no verified, packaged Windows executable yet. Do not claim this requirement is complete merely because `python main.py` works.
6. **Automatic analysis:** file selection now begins analysis without an extra Start Analysis step. Confirm demo flow.

## Remaining technical risks, not fixed or not fully verified

- Exact forensic history cannot be recovered when the source DOCX lacks genuine RSIDs or metadata. Do not manufacture it.
- The document-order player is **not** a chronological editing-session movie. This is a substantive FR-7 gap.
- XML edge cases (tracked changes, deleted text, embedded fields, hyperlinks, footnotes, complex tables) need wider forensic test samples. The run-to-word allocation is deterministic, not infallible.
- `docProps` properties can be stale, altered by conversions, or missing. Ratios are descriptive, not valid attribution or misconduct metrics.
- Complete Windows GUI, PDF-save dialog, packaging, Windows 10 compatibility, high-volume cases, and concurrent instances require hands-on testing.
- Some scripts and session storage use local project paths in source mode; runtime data must **never** be committed to GitHub.
- The client has not supplied a complete time-based session history method or final acceptance sign-off on the analytics.
