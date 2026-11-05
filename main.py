from pathlib import Path
import os

# Use the browser engine shipped with the application, rather than WebView2.
os.environ["QT_API"] = "pyside6"

import webview
from core.document_reader import read_docx
from core.analysis_store import AnalysisStore
from core.session_manager import SessionError

class Api:
    def __init__(self):
        self.store = AnalysisStore()

    def read_docx(self, filename, encoded_file):
        result = read_docx(filename, encoded_file)
        if result.get('success'):
            try:
                result['session_id'] = self.store.save(filename, result)
            except (SessionError, OSError, ValueError) as error:
                result['storage_error'] = f'Analysis completed, but could not be saved: {error}'
        return result

    def list_sessions(self):
        try:
            return {'success': True, 'sessions': self.store.list()}
        except (SessionError, OSError) as error:
            return {'success': False, 'message': str(error)}

    def load_analysis(self, session_id):
        try:
            filename, result = self.store.open(session_id)
            return {**result, 'filename': filename, 'session_id': session_id}
        except (SessionError, OSError, ValueError, KeyError, TypeError) as error:
            return {'success': False, 'message': f'Unable to open saved analysis: {error}'}

    def export_analysis(self, session_id):
        try:
            filename, _ = self.store.open(session_id)
            destination = webview.windows[0].create_file_dialog(
                webview.FileDialog.SAVE, save_filename=Path(filename).stem + '-analysis.html',
                file_types=('HTML report (*.html)',))
            if not destination:
                return {'success': True, 'cancelled': True}
            path = destination if isinstance(destination, str) else destination[0]
            saved = self.store.export(session_id, path)
            return {'success': True, 'path': str(saved)}
        except (SessionError, OSError, ValueError, KeyError, TypeError) as error:
            return {'success': False, 'message': f'Unable to export report: {error}'}

if __name__ == "__main__":
    api = Api()

    webview.create_window(
        title="Document Metadata Extractor",
        url=str(Path(__file__).resolve().parent / "ui" / "index.html"),
        js_api=api,
        maximized=True,
        width=1200,
        height=800,
        min_size=(900, 600),
        resizable=True
    )

    webview.start(gui="qt", debug=False)
