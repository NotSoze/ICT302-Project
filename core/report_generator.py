"""
@file report_generator.py
@brief Creates a local HTML summary of a completed CopyQ analysis.
"""

from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


def generate_html_report(
    analysis_result: dict[str, Any],
    destination: str | Path,
) -> Path:
    """
    @brief Write a readable HTML report for a successful analysis.

    @param analysis_result Result dictionary returned by AnalysisPipeline.analyse().
    @param destination Output path for the HTML report.
    @return The saved report path.
    """
    if not isinstance(analysis_result, dict) or not analysis_result.get("ok"):
        raise ValueError("analysis_result must contain a successful analysis")

    document = analysis_result.get("document", {})
    metrics = analysis_result.get("metrics", {})
    integrity = analysis_result.get("integrity", {})
    top_sessions = analysis_result.get("top_sessions", [])

    if not isinstance(document, dict) or not isinstance(metrics, dict):
        raise ValueError("analysis_result has an invalid document or metrics section")

    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    document_metadata = document.get("metadata", {})
    rows = [
        ("Document ID", document.get("document_id")),
        ("Original SHA-256", integrity.get("original_sha256")),
        ("Working copy verified", integrity.get("working_copy_verified")),
        ("RSID root", document.get("rsid_root")),
        ("Creation date", document_metadata.get("creation_date")),
        ("Modified date", document_metadata.get("modified_date")),
        ("Revision count", metrics.get("revision_count")),
        ("Total word count", metrics.get("total_word_count")),
        ("Unique RSID count", metrics.get("unique_rsid_count")),
        ("Word-to-revision ratio", metrics.get("word_to_revision_ratio")),
        (
            "Unique-RSID-to-revision ratio",
            metrics.get("unique_rsid_to_revision_ratio"),
        ),
    ]

    summary_rows = "\n".join(
        (
            "<tr>"
            f"<th>{escape(str(label))}</th>"
            f"<td>{_display(value)}</td>"
            "</tr>"
        )
        for label, value in rows
    )

    session_rows = "\n".join(
        (
            "<tr>"
            f"<td>{_display(session.get('rsid'))}</td>"
            f"<td>{_display(session.get('word_count'))}</td>"
            f"<td>{_display(session.get('session_type'))}</td>"
            "</tr>"
        )
        for session in top_sessions
        if isinstance(session, dict)
    )

    if not session_rows:
        session_rows = (
            "<tr><td colspan='3'>No RSID session data was available.</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CopyQ Analysis Report</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      line-height: 1.5;
      margin: 2rem;
      color: #1f2933;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin-bottom: 2rem;
    }}
    th, td {{
      border: 1px solid #cbd5e1;
      padding: 0.6rem;
      text-align: left;
    }}
    th {{
      background: #e2e8f0;
    }}
    .notice {{
      background: #eff6ff;
      border-left: 4px solid #2563eb;
      padding: 1rem;
    }}
  </style>
</head>
<body>
  <h1>CopyQ Analysis Report</h1>

  <p class="notice">
    This report describes document metadata and editing-session indicators.
    It does not determine whether academic misconduct occurred.
  </p>

  <h2>Document summary</h2>
  <table>
    {summary_rows}
  </table>

  <h2>Top editing sessions</h2>
  <table>
    <thead>
      <tr>
        <th>RSID</th>
        <th>Word count</th>
        <th>Session type</th>
      </tr>
    </thead>
    <tbody>
      {session_rows}
    </tbody>
  </table>
</body>
</html>
"""

    # Write to a temporary file first so an interrupted save does not leave
    # a partially written report at the requested destination.
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".tmp",
        dir=output_path.parent,
        delete=False,
    ) as temporary_file:
        temporary_file.write(html)
        temporary_path = Path(temporary_file.name)

    temporary_path.replace(output_path)
    return output_path


def _display(value: Any) -> str:
    """
    @brief Convert a report value into safe HTML text.
    """
    if value is None or value == "":
        return "Not available"

    return escape(str(value))