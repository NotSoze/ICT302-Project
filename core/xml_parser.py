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
                    
                runs_data.append({
                    'rsidR': r_rsid_r,
                    'text': run_text
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
            'revision_count': 1  # Default fallback if revision element is missing
        }
        
        if self.core_root is None:
            return metadata

        # Extract creation date
        created_elem = self.core_root.find('.//dcterms:created', self.NS) or self.core_root.find('.//dc:created', self.NS)
        if created_elem is not None and created_elem.text:
            metadata['creation_date'] = created_elem.text

        # Extract modification date
        modified_elem = self.core_root.find('.//dcterms:modified', self.NS) or self.core_root.find('.//dc:modified', self.NS)
        if modified_elem is not None and modified_elem.text:
            metadata['modified_date'] = modified_elem.text

        # Extract document revision count from core properties (<cp:revision>)
        revision_elem = self.core_root.find('.//cp:revision', self.NS)
        if revision_elem is not None and revision_elem.text:
            try:
                metadata['revision_count'] = int(revision_elem.text.strip())
            except ValueError:
                metadata['revision_count'] = 1

        return metadata