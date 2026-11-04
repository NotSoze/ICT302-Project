"""Adapt the DOCX backend's results for the desktop frontend.

The parser owns paragraph analysis and metadata; the calculator owns metrics.
This module transfers uploaded bytes to the document handler, builds preview
HTML, and returns analysis and integrity results to frontend/script.js.
"""
import base64
import binascii
import os
from uuid import uuid4
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET
from zipfile import BadZipFile

from core.docx_unzipper import DocxUnzipper
from core.xml_parser import XMLParser
from core.metrics_calculator import MetricsCalculator
from core.doc_handler import handle_upload, verify_working_copy
from core.verification_log import Event, VerificationLog, LogIntegrityError

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def render(element, paragraph_indices=None, default_run_rsid=''):
    tag = element.tag.removeprefix(W)
    if tag == 'p':
        default_run_rsid = element.get(W + 'rsidRDefault', '')
    if tag == 't':
        return escape(element.text or '')
    if tag == 'tab':
        return '&#9;'
    if tag in ('br', 'cr'):
        return '<br>'
    if tag in ('pPr', 'rPr', 'tblPr', 'trPr', 'tcPr', 'del'):
        return ''
    content = ''.join(render(child, paragraph_indices, default_run_rsid) for child in element)
    if tag == 'r':
        props = element.find(W + 'rPr')
        if props is not None:
            for name, html_tag in [('b', 'strong'), ('i', 'em'), ('u', 'u')]:
                prop = props.find(W + name)
                if prop is not None and prop.get(W + 'val', '1') not in ('0', 'false', 'off', 'none'):
                    content = f'<{html_tag}>{content}</{html_tag}>'
        # rsidRDefault applies to runs without their own rsidR. A paragraph's
        # rsidR describes the paragraph addition, so do not use it for run text.
        rsid = escape(element.get(W + 'rsidR', default_run_rsid), quote=True)
        content = f'<span class="rsid-run" data-rsid="{rsid}">{content}</span>'
    if tag == 'p':
        rsid = escape(element.get(W + 'rsidR', ''), quote=True)
        style = element.find(f'{W}pPr/{W}pStyle')
        if style is not None and style.get(W + 'val', '').lower().startswith('heading'):
            content = f'<strong>{content}</strong>'
        index = (paragraph_indices or {}).get(id(element), '')
        return f'<p data-rsid="{rsid}" data-analysis-index="{index}">{content}</p>'
    html_tag = {'tbl': 'table', 'tr': 'tr', 'tc': 'td'}.get(tag)
    return f'<{html_tag}>{content}</{html_tag}>' if html_tag else content


def read_docx(filename, encoded_file, storage_dir=None):
    # Guard the bridge input, not the document format (owned by validation.py).
    if (not isinstance(filename, str) or not filename or filename in ('.', '..')
            or any(character in filename for character in '/\\:\x00')):
        return {'success': False, 'message': 'Invalid upload filename.'}
    try:
        data = base64.b64decode(encoded_file, validate=True)
        storage = (Path(storage_dir) if storage_dir is not None else
                   Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'MetadataApp' / 'storage')
        log_path = storage / 'verification_logs' / f'{uuid4().hex}.jsonl'
        log = VerificationLog(log_path)
        # Stage the browser's upload bytes. The handler owns the verified copy;
        # neither this adapter nor the frontend opens the user's original for writing.
        with TemporaryDirectory(prefix='metadata-docx-') as directory:
            uploaded = Path(directory) / filename
            uploaded.write_bytes(data)
            accepted, message, check = handle_upload(uploaded, Path(directory) / 'working', log)
            if not accepted:
                return {'success': False, 'message': message,
                        'warnings': check['warnings'], 'verification_log': str(log_path)}
            working_copy = Path(check['working_path'])
            log.write(Event.ANALYSIS_STARTED, file_name=filename)
            buffers = DocxUnzipper(working_copy).extract_xml_buffers()
            result = analyze_buffers(buffers)
            unchanged = verify_working_copy(working_copy, check['sha256'])
            log.write(Event.REVERIFY_MATCH if unchanged else Event.REVERIFY_MISMATCH,
                      file_name=filename, sha256=check['sha256'])
            if not unchanged:
                return {'success': False, 'message': 'Working copy changed during analysis.',
                        'verification_log': str(log_path)}
            log.write(Event.ANALYSIS_DONE, file_name=filename)
            result.update(warnings=check['warnings'], sha256=check['sha256'],
                          integrity_verified=True, verification_log=str(log_path))
            return result
    except (BadZipFile, ET.ParseError, binascii.Error, ValueError, TypeError):
        return {'success': False, 'message': 'Unable to read this DOCX: invalid ZIP, XML, or file data.'}
    except LogIntegrityError:
        return {'success': False, 'message': 'The verification log failed its integrity check.'}
    except OSError:
        return {'success': False, 'message': 'Unable to create or read the local document working copy or verification log.'}


def analyze_buffers(buffers):
    """Render and analyze XML already validated and extracted by the intake pipeline."""
    parser = XMLParser(buffers)
    paragraphs = parser.parse_document_structure()
    metadata = parser.extract_core_metadata()
    calculator = MetricsCalculator(paragraphs, metadata)
    # Match XMLParser.parse_document_structure's traversal exactly, including
    # empty paragraphs and paragraphs inside tables. Do not depend on helper
    # methods outside the supplied parser's public interface. Deleted content
    # is hidden by the preview, but retains its position in the analysis list.
    paragraph_elements = buffers['document_xml'].iterfind(f'.//{W}p')
    indices = {id(p): index for index, p in enumerate(paragraph_elements)}
    return {
        'success': True,
        'html': render(buffers['document_xml'], indices),
        'paragraphs': paragraphs,
        'metadata': metadata,
        'rsid_root': parser.extract_rsid_root(),
        'metrics': calculator.compute_macro_metrics(),
        'top_sessions': calculator.generate_top_n_rankings(),
    }
