"""Generate an offline PDF report from the completed CopyQ analysis.

Uses ReportLab to avoid relying on a browser, network, or HTML-to-PDF engine.
All indicators are descriptive and must not be treated as a misconduct verdict.
"""
import colorsys
from datetime import datetime
from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def _display(value: Any) -> str:
    if value is None or value == "":
        return "Not available"
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    return str(value)


def _format_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return "Not available"
    try:
        parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        return parsed.strftime('%Y-%m-%d %H:%M:%S %z').strip()
    except ValueError:
        return value


def _rsid_colour(index: int):
    hue = ((index * 137.508 + 30) % 360) / 360
    r, g, b = colorsys.hls_to_rgb(hue, .82, .70)
    return colors.Color(r, g, b)


def _safe_text(text) -> str:
    return escape(_display(text)).replace('\n', '<br/>')


def generate_pdf_report(analysis_result: dict[str, Any], destination: str | Path) -> Path:
    """Produce a PDF report with metadata, descriptive metrics and text-run grouping.

    Output is generated in a temporary file and atomically moved into place.
    """
    if not isinstance(analysis_result, dict) or not analysis_result.get('ok'):
        raise ValueError('A successful analysis is required to generate a report.')
    document = analysis_result.get('document') or {}
    metadata = document.get('metadata') or {}
    metrics = analysis_result.get('metrics') or {}
    integrity = analysis_result.get('integrity') or {}
    top_sessions = analysis_result.get('top_sessions') or []
    paragraphs = analysis_result.get('paragraphs') or []
    notices = analysis_result.get('analysis_notices') or []
    output = Path(destination)
    if output.suffix.lower() != '.pdf':
        raise ValueError('Report destination must end in .pdf.')
    output.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CopyQTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=19, leading=24, spaceAfter=14))
    styles.add(ParagraphStyle(name='CopyQSmall', fontName='Helvetica', fontSize=8.8, leading=12.5, spaceAfter=8))
    styles.add(ParagraphStyle(name='CopyQBody', fontName='Helvetica', fontSize=9.2, leading=13, spaceAfter=7))
    styles.add(ParagraphStyle(name='CopyQSection', parent=styles['Heading2'], spaceBefore=15, spaceAfter=8))
    styles.add(ParagraphStyle(name='CopyQText', fontName='Helvetica', fontSize=8.6, leading=12, spaceAfter=8, borderPadding=5))

    story = [Paragraph('CopyQ — Forensic Document Analysis', styles['CopyQTitle'])]
    story.append(Paragraph('Local, descriptive evidence summary. This document does not determine authorship, pasting, or academic misconduct.', styles['CopyQBody']))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#999999')))
    story.append(Paragraph('Document metadata and integrity', styles['CopyQSection']))

    metadata_rows = [
        ('Document / session ID', document.get('document_id')),
        ('Original SHA-256', integrity.get('original_sha256')),
        ('Working copy verified', integrity.get('working_copy_verified')),
        ('Root RSID', document.get('rsid_root')),
        ('Creator', metadata.get('creator')),
        ('Last modified by', metadata.get('last_modified_by')),
        ('Created', _format_timestamp(metadata.get('creation_date'))),
        ('Last modified', _format_timestamp(metadata.get('modified_date'))),
        ('Application', metadata.get('application')),
        ('Application version', metadata.get('app_version')),
        ('Reported editing time (min)', metadata.get('editing_time_minutes')),
        ('Recorded page count', metadata.get('page_count')),
        ('Shared document', metadata.get('shared_document')),
    ]
    measurement_rows = [
        ('Total extracted words', metrics.get('total_word_count')),
        ('Recorded revision count', metrics.get('revision_count')),
        ('Distinct usable RSIDs', metrics.get('unique_rsid_count')),
        ('Nonempty OOXML text runs', metrics.get('text_run_count')),
        ('Words attributed to usable RSIDs', metrics.get('attributed_word_count')),
        ('Words / recorded revision', metrics.get('word_to_revision_ratio')),
        ('RSIDs / recorded revision', metrics.get('unique_rsid_to_revision_ratio')),
        ('Largest RSID group (words)', metrics.get('largest_rsid_word_count')),
        ('Largest RSID group (%)', metrics.get('largest_rsid_share_percent')),
        ('Avg characters / usable RSID', metrics.get('average_characters_per_rsid')),
        ('Avg characters / nonempty run', metrics.get('average_characters_per_run')),
    ]

    def add_table(rows):
        cells = [[Paragraph(_safe_text(label), styles['CopyQSmall']),
                  Paragraph(_safe_text(value), styles['CopyQSmall'])] for label, value in rows]
        table = Table(cells, colWidths=[62 * mm, 114 * mm], hAlign='LEFT')
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f2f2f5')),
            ('LINEBELOW', (0, 0), (-1, -1), .3, colors.HexColor('#dddddd')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

    add_table(metadata_rows)
    story.append(Paragraph('Descriptive document measurements', styles['CopyQSection']))
    add_table(measurement_rows)
    story.append(Paragraph('Analysis limitations and observations', styles['CopyQSection']))
    if metrics.get('unique_rsid_count') == 0:
        story.append(Paragraph('No usable RSIDs were found; zero-filled or missing identifiers cannot distinguish editing sessions.', styles['CopyQBody']))
    else:
        share = metrics.get('largest_rsid_share_percent')
        if share is not None:
            story.append(Paragraph(f'The largest usable RSID group accounts for {share}% of extracted words. This does not demonstrate misconduct or a paste event.', styles['CopyQBody']))
    for indicator in metrics.get('descriptive_indicators') or []:
        story.append(Paragraph('Review indicator: ' + _safe_text(indicator.get('description')), styles['CopyQBody']))
    if metrics.get('revision_count') is None:
        story.append(Paragraph('Revision count was absent or unusable, so division by revision count was not performed.', styles['CopyQBody']))
    for note in notices:
        story.append(Paragraph(_safe_text(note), styles['CopyQBody']))
    story.append(Paragraph('RSID values have no reliable per-session timestamps; any coloured text below follows current document order, not a verified editing chronology.', styles['CopyQBody']))
    story.append(Paragraph('Largest RSID-associated text groups', styles['CopyQSection']))
    if top_sessions:
        groups = [['RSID', 'Attributed words', 'Group']]
        for entry in top_sessions:
            groups.append([_display(entry.get('rsid')), _display(entry.get('word_count')), _display(entry.get('session_type'))])
        group_table = Table(groups, colWidths=[80 * mm, 48 * mm, 48 * mm], repeatRows=1)
        group_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8ed')),
            ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#dddddd')),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(group_table)
    else:
        story.append(Paragraph('No usable RSID groups available.', styles['CopyQBody']))

    if paragraphs:
        story.append(Paragraph('Current document text — paragraph-level visual overview', styles['CopyQSection']))
        story.append(Paragraph('Paragraphs are shown in current document order, with a pale background indicating their RSID grouping when one is available. Groups are not verified edit times.', styles['CopyQBody']))
        sequence = analysis_result.get('session_sequence') or []
        colour_by_rsid = {rsid.upper(): _rsid_colour(index) for index, rsid in enumerate(sequence)}
        # Render all paragraphs, not just a silent top-N subset. Paragraphs can
        # naturally flow across PDF pages if they are long.
        for i, paragraph in enumerate(paragraphs, 1):
            content = paragraph.get('text') or ''
            if not content.strip():
                continue
            present = [r.get('rsidR') for r in paragraph.get('runs', []) if r.get('rsidR')]
            rsid = present[0].upper() if present else None
            info = f'Paragraph {i} · {paragraph.get("word_count", 0)} words · RSID {rsid or "Unavailable"}'
            story.append(Paragraph(_safe_text(info), styles['CopyQSmall']))
            para_style = ParagraphStyle('P_' + str(i), parent=styles['CopyQText'],
                                        backColor=colors.HexColor('#f8f8f8'), borderPadding=6)
            coloured_runs = []
            for run in paragraph.get('runs', []):
                raw = run.get('text', '')
                if not raw:
                    continue
                colour = colour_by_rsid.get((run.get('rsidR') or '').upper())
                if colour:
                    hex_colour = '#' + colour.hexval()[-6:]
                    coloured_runs.append('<font backColor="' + hex_colour + '">' + _safe_text(raw) + '</font>')
                else:
                    coloured_runs.append(_safe_text(raw))
            story.append(Paragraph(''.join(coloured_runs) if coloured_runs else _safe_text(content), para_style))
            story.append(Spacer(1, 3 * mm))

    def footer(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawRightString(A4[0] - 16 * mm, 12 * mm, f'CopyQ · Page {doc.page}')

    with NamedTemporaryFile(mode='wb', suffix='.pdf', dir=output.parent, delete=False) as file:
        temp = Path(file.name)
    try:
        pdf = SimpleDocTemplate(str(temp), pagesize=A4, leftMargin=17 * mm,
                                rightMargin=17 * mm, topMargin=18 * mm, bottomMargin=20 * mm)
        pdf.build(story, onFirstPage=footer, onLaterPages=footer)
        if not temp.read_bytes().startswith(b'%PDF-'):
            raise ValueError('PDF report generation failed.')
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)
    return output


# Retain the previous symbol for older code paths, while the output is a PDF.
generate_html_report = generate_pdf_report
