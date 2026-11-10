import xml.etree.ElementTree as ET

class XMLParser:
    """
    Parses OOXML elements to extract rsidRoot, paragraphs, text runs, and session mappings.
    """
    # Namespaces commonly used in OOXML
    NS = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/'
    }

    def __init__(self, xml_buffers: dict):
        self.document_root = xml_buffers.get('document_xml')
        self.settings_root = xml_buffers.get('settings_xml')
        self.core_root = xml_buffers.get('core_xml')

    def extract_rsid_root(self) -> str | None:
        """
        Extracts the authoritative Primary session identifier (w:rsidRoot) from settings.xml.
        """
        if self.settings_root is None:
            return None
        
        # Look for <w:rsidRoot w:val="XXXXXXXX"/>
        rsid_root_elem = self.settings_root.find('.//w:rsidRoot', self.NS)
        if rsid_root_elem is not None:
            return rsid_root_elem.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
        return None

    def parse_document_structure(self) -> list[dict]:
        """
        Scans document.xml to extract paragraphs, text runs, word counts, and rsidR values.
        """
        if self.document_root is None:
            return []

        parsed_paragraphs = []
        rsid_root = self.extract_rsid_root()

        # Iterate through paragraphs <w:p>
        for p in self.document_root.iterfind('.//w:p', self.NS):
            p_rsid_r = p.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsidR')
            p_rsid_default = p.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsidRDefault')
            
            p_text = ""
            runs_data = []

            # Iterate through text runs <w:r> inside the paragraph
            for r in p.iterfind('.//w:r', self.NS):
                r_rsid_r = r.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsidR')
                
                t_elem = r.find('.//w:t', self.NS)
                run_text = t_elem.text if (t_elem is not None and t_elem.text) else ""
                
                if t_elem is not None and t_elem.text:
                    p_text += t_elem.text

                # 1. Apply the fallback cascade so untagged runs inherit paragraph RSIDs
                effective_run_rsid = r_rsid_r or p_rsid_r or p_rsid_default
                
                # 2. Compute run-level word count
                run_word_count = len(run_text.split()) if run_text else 0
                
                # 3. Classify run-level session type against rsid_root
                run_session_type = (
                    "Primary"
                    if (effective_run_rsid and rsid_root and effective_run_rsid.lower() == rsid_root.lower())
                    else "Secondary/Other"
                )
                    
                runs_data.append({
                    'rsidR': effective_run_rsid,
                    'text': run_text,
                    'word_count': run_word_count,
                    'session_type': run_session_type
                })

            word_count = len(p_text.split())

            # Classify session type based strictly on rsidRoot comparison
            active_rsid = p_rsid_r or p_rsid_default
            session_type = "Primary" if (active_rsid and rsid_root and active_rsid.lower() == rsid_root.lower()) else "Secondary/Other"

            parsed_paragraphs.append({
                'paragraph_rsidR': p_rsid_r,
                'paragraph_rsidDefault': p_rsid_default,
                'session_type': session_type,
                'word_count': word_count,
                'text': p_text,
                'runs': runs_data
            })

        return parsed_paragraphs

    def extract_core_metadata(self) -> dict:
        """
        Extracts document-level metadata from core.xml, including creation date, 
        modification date, and the official document revision count (<cp:revision>).
        """
        metadata = {
            'creation_date': None,
            'modified_date': None,
            'creator': None,
            'last_modified_by': None,
            'revision_count': 1  # Default fallback if revision element is missing
        }
        
        if self.core_root is None:
            return metadata

        # Iterate through all elements and match local tag names, bypassing namespace prefix quirks
        for elem in self.core_root.iter():
            # ElementTree formats tags with namespaces as '{uri}local_tag'
            local_tag = elem.tag.split('}')[-1].lower()
            
            if local_tag == 'created' and elem.text:
                metadata['creation_date'] = elem.text.strip()
            elif local_tag == 'modified' and elem.text:
                metadata['modified_date'] = elem.text.strip()
            elif local_tag == 'creator' and elem.text:
                metadata['creator'] = elem.text.strip()
            elif local_tag == 'lastmodifiedby' and elem.text:
                metadata['last_modified_by'] = elem.text.strip()
            elif local_tag == 'revision' and elem.text:
                try:
                    metadata['revision_count'] = int(elem.text.strip())
                except ValueError:
                    metadata['revision_count'] = 1

        return metadata

    def generate_timeline_player_sequence(self, parsed_paragraphs: list[dict]) -> list[dict]:
        """
        Constructs the session sequence using the order of RSIDs in settings.xml.
        """
        if self.settings_root is None:
            return []

        # 1. Get all unique RSIDs in their exact chronological order from settings.xml
        settings_rsids = []
        for elem in self.settings_root.iter():
            local_tag = elem.tag.split('}')[-1]
            if local_tag == 'rsid':
                val = elem.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                if val and val not in settings_rsids:
                    settings_rsids.append(val)

        rsid_root = self.extract_rsid_root()
        timeline_sessions = []

        # 2. Iterate through each RSID value in settings.xml order (top to bottom)
        for target_rsid in settings_rsids:
            session_total_words = 0
            session_texts = []
            
            # Determine session type based on whether this RSID is the root RSID
            is_root = (rsid_root and target_rsid.lower() == rsid_root.lower())
            session_type = "Primary" if is_root else "Secondary/Other"

            # 3. Iterate through all paragraph objects of the document
            for para in parsed_paragraphs:
                # Go into the paragraph objects to find the text run level objects
                for run in para.get('runs', []):
                    run_rsid = run.get('rsidR')
                    
                    # Match with the target RSID from settings.xml
                    if run_rsid and run_rsid.lower() == target_rsid.lower():
                        # Accumulate word counts
                        session_total_words += run.get('word_count', 0)
                        
                        # Take its string (combine if multiple found)
                        if run.get('text'):
                            session_texts.append(run['text'])

            # 4. Only keep sessions that actually appear in the document text
            if session_texts:
                timeline_sessions.append({
                    'rsid': target_rsid,
                    'total_word_count': session_total_words,
                    'combined_text': "".join(session_texts),
                    'session_type': session_type
                })

        return timeline_sessions
