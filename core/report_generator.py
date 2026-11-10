"""
@file report_generator.py
@brief Creates a local HTML summary of a completed CopyQ analysis.
"""

from datetime import datetime
from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from xhtml2pdf import pisa

def _format_timestamp(raw_date: Any) -> str:
    """
    @brief Convert an ISO timestamp string into a human-readable format.
    """
    if not isinstance(raw_date, str) or not raw_date.strip():
        return "Not available"
    try:
        # Parse ISO format (handling trailing 'Z' for UTC)
        cleaned = raw_date.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt.strftime("%B %d, %Y at %H:%M UTC")
    except ValueError:
        # Fallback to raw string if parsing fails
        return raw_date

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
        ("Author", document_metadata.get("creator")),
        ("Last modified by", document_metadata.get("last_modified_by")),
        ("Creation date", _format_timestamp(document_metadata.get("creation_date"))),
        ("Modified date", _format_timestamp(document_metadata.get("modified_date"))),
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
      width: 100%;
      margin-bottom: 2rem;
    }}
    th, td {{
      border: 1px solid #cbd5e1;
      padding: 0.6rem;
      padding-left: 0;
      padding-top: 0.8rem;
      margin-left: 0;
      text-align: left;
      font-size: 0.85rem;
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
  <table cellpadding="0" cellspacing="0">
    <colgroup>
      <col style="width: 20%;">
      <col style="width: 80%;">
    </colgroup>
    {summary_rows}
  </table>

  <h2>Top editing sessions</h2>
  <table cellpadding="0" cellspacing="0">
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

    


    with NamedTemporaryFile(
        mode="w+b", # 👈 Note: Changed from text mode ("w") to binary write mode ("w+b")
        suffix=".tmp",
        dir=output_path.parent,
        delete=False,
    ) as temporary_file:
        pisa_status = pisa.CreatePDF(html, dest=temporary_file) # 👈 Converts HTML to PDF binary stream
        temporary_path = Path(temporary_file.name)

    if pisa_status.err:
        raise ValueError("Failed to generate PDF report from HTML template.")

    temporary_path.replace(output_path)
    return output_path


def _display(value: Any) -> str:
    """
    @brief Convert a report value into safe HTML text.
    """
    if value is None or value == "":
        return "Not available"

    return escape(str(value))