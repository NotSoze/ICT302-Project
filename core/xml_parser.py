"""Read WordprocessingML text, RSIDs, and document properties.

RSIDs label editing contexts, *not* authors or timestamps. Missing/zero RSIDs
are not counted as sessions. Word attribution across fragmented XML runs is an
explicit, deterministic approximation (majority of characters in each token).
"""
import re


RSID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}$")
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def usable_rsid(value):
    """Return a normalized RSID, or None if absent/placeholder/invalid."""
    if not isinstance(value, str) or not RSID_PATTERN.fullmatch(value):
        return None
    value = value.upper()
    return value if value != '00000000' else None


class XMLParser:
    NS = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/',
    }

    def __init__(self, xml_buffers: dict):
        self.document_root = xml_buffers.get('document_xml')
        self.settings_root = xml_buffers.get('settings_xml')
        self.core_root = xml_buffers.get('core_xml')
        self.app_root = xml_buffers.get('app_xml')

    def extract_rsid_root(self) -> str | None:
        if self.settings_root is None:
            return None
        rsid_root_elem = self.settings_root.find('.//w:rsidRoot', self.NS)
        return usable_rsid(rsid_root_elem.get(W + 'val')) if rsid_root_elem is not None else None

    @staticmethod
    def _run_text(run):
        pieces = []
        for element in run.iter():
            if element.tag == W + 't':
                pieces.append(element.text or '')
            elif element.tag == W + 'tab':
                pieces.append('\t')
            elif element.tag in (W + 'br', W + 'cr'):
                pieces.append('\n')
        return ''.join(pieces)

    @staticmethod
    def _allocate_words(full_text, spans, runs):
        """Count each *whole paragraph token* once, attributing it to one run.

        Tokens may span multiple OOXML runs. Choose the run that contributed
        most non-whitespace characters (first run wins ties); do not count the
        same token twice. This is a descriptive allocation, not edit chronology.
        """
        for match in re.finditer(r'\S+', full_text):
            start, end = match.span()
            candidates = []
            for index, (left, right) in enumerate(spans):
                overlap = max(0, min(end, right) - max(start, left))
                if overlap:
                    candidates.append((overlap, -index, index))
            if candidates:
                winner = max(candidates)[2]
                runs[winner]['word_count'] += 1

    def parse_document_structure(self) -> list[dict]:
        if self.document_root is None:
            return []
        paragraphs = []
        root_rsid = self.extract_rsid_root()
        for paragraph in self.document_root.iterfind('.//w:p', self.NS):
            p_rsid = paragraph.get(W + 'rsidR')
            p_default = paragraph.get(W + 'rsidRDefault')
            active = usable_rsid(p_rsid) or usable_rsid(p_default)
            session_type = self._session_type(active, root_rsid)
            runs = []
            spans = []
            text_parts = []
            position = 0
            for run in paragraph.iterfind('.//w:r', self.NS):
                run_text = self._run_text(run)
                # w:rsidRDefault is defined as the default for runs lacking
                # their own rsidR; the paragraph addition RSID is not fallback.
                raw_rsid = run.get(W + 'rsidR') or p_default
                effective = usable_rsid(raw_rsid)
                runs.append({
                    'rsidR': effective,
                    'raw_rsidR': raw_rsid,
                    'text': run_text,
                    'word_count': 0,
                    'character_count': len(run_text),
                    'session_type': self._session_type(effective, root_rsid),
                })
                text_parts.append(run_text)
                spans.append((position, position + len(run_text)))
                position += len(run_text)
            full_text = ''.join(text_parts)
            self._allocate_words(full_text, spans, runs)
            paragraphs.append({
                'paragraph_rsidR': p_rsid,
                'paragraph_rsidDefault': p_default,
                'session_type': session_type,
                'word_count': len(re.findall(r'\S+', full_text)),
                'text': full_text,
                'runs': runs,
            })
        return paragraphs

    @staticmethod
    def _session_type(rsid, root):
        if not rsid:
            return 'Unavailable'
        if not root:
            return 'Unclassified'
        if rsid == root:
            return 'Root'
        return 'Other'

    def extract_core_metadata(self) -> dict:
        metadata = {
            'creation_date': None, 'modified_date': None,
            'creator': None, 'last_modified_by': None,
            'revision_count': None, 'application': None, 'app_version': None,
            'editing_time_minutes': None, 'page_count': None,
            'shared_document': None,
        }
        core_map = {'created': 'creation_date', 'modified': 'modified_date',
                    'creator': 'creator', 'lastmodifiedby': 'last_modified_by',
                    'revision': 'revision_count'}
        app_map = {'application': 'application', 'appversion': 'app_version',
                   'totaltime': 'editing_time_minutes', 'pages': 'page_count',
                   'shareddoc': 'shared_document'}
        for root, mapping in ((self.core_root, core_map), (self.app_root, app_map)):
            if root is None:
                continue
            for item in root.iter():
                key = mapping.get(item.tag.split('}')[-1].lower())
                if not key or not item.text or not item.text.strip():
                    continue
                value = item.text.strip()
                if key in ('revision_count', 'editing_time_minutes', 'page_count'):
                    try:
                        value = int(value)
                        if value < 0:
                            continue
                    except ValueError:
                        continue
                elif key == 'shared_document':
                    if value.lower() not in ('true', 'false', '1', '0'):
                        continue
                    value = value.lower() in ('true', '1')
                metadata[key] = value
        return metadata

    def generate_timeline_player_sequence(self, parsed_paragraphs: list[dict]) -> list[dict]:
        """RSID groups in order of FIRST APPEARANCE IN DOCUMENT, not time.

        Neither the order of settings.xml's rsid table nor the hex identifier
        provides a trustworthy editing chronology. Only meaningful IDs enter.
        """
        grouped = {}
        root = self.extract_rsid_root()
        for paragraph in parsed_paragraphs:
            for run in paragraph.get('runs', []):
                rsid = usable_rsid(run.get('rsidR'))
                if not rsid:
                    continue
                if rsid not in grouped:
                    grouped[rsid] = {'rsid': rsid, 'total_word_count': 0,
                                     'combined_text': '',
                                     'session_type': self._session_type(rsid, root)}
                grouped[rsid]['total_word_count'] += run.get('word_count', 0)
                grouped[rsid]['combined_text'] += run.get('text', '')
        return list(grouped.values())
