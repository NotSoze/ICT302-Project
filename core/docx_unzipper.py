import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

class DocxUnzipper:
    """
    Extracts essential XML components from a validated .docx working copy.
    """
    def __init__(self, docx_path: str | Path):
        self.docx_path = Path(docx_path)

    def extract_xml_buffers(self) -> dict:
        """
        Unzips the document and returns ElementTree roots for document.xml, settings.xml, and core.xml.
        """
        if not self.docx_path.exists():
            raise FileNotFoundError(f"Working copy not found at: {self.docx_path}")

        buffers = {}
        with zipfile.ZipFile(self.docx_path, 'r') as zf:
            namelist = zf.namelist()
            
            # Extract document.xml
            if 'word/document.xml' in namelist:
                with zf.open('word/document.xml') as f:
                    buffers['document_xml'] = ET.parse(f).getroot()
            
            # Extract settings.xml (contains w:rsidRoot)
            if 'word/settings.xml' in namelist:
                with zf.open('word/settings.xml') as f:
                    buffers['settings_xml'] = ET.parse(f).getroot()
                    
            # Extract core.xml (contains metadata/editing time)
            if 'package/metadata' in namelist or 'docProps/core.xml' in namelist:
                core_path = 'docProps/core.xml' if 'docProps/core.xml' in namelist else 'package/metadata' # fallback check
                with zf.open(core_path) as f:
                    buffers['core_xml'] = ET.parse(f).getroot()
                    
        return buffers