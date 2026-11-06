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
        project_storage = Path(__file__).resolve().parent / "storage" / "sessions"
        self.store = AnalysisStore(directory=project_storage)

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

    def delete_analysis(self, session_id):
        try:
            success = self.store.delete(session_id)
            if success:
                return {'success': True}
            return {'success': False, 'message': 'Session file not found.'}
        except (SessionError, OSError, ValueError, KeyError, TypeError) as error:
            return {'success': False, 'message': f'Unable to delete saved analysis: {error}'}

    def list_temp_workspaces(self):
        try:
            temp_dir = Path(__file__).resolve().parent / "storage" / "temp_workspace"
            if not temp_dir.exists():
                return {'success': True, 'workspaces': []}
            
            workspaces = []
            for item in temp_dir.iterdir():
                if item.is_dir():
                    size_bytes = sum(f.stat().st_size for f in item.glob('**/*') if f.is_file())
                    workspaces.append({
                        'id': item.name,
                        'name': item.name,
                        'size': size_bytes,
                        'modified_at': item.stat().st_mtime
                    })
            return {'success': True, 'workspaces': sorted(workspaces, key=lambda x: x['modified_at'], reverse=True)}
        except (OSError, Exception) as error:
            return {'success': False, 'message': str(error)}

    def delete_temp_workspace(self, workspace_id):
        try:
            temp_dir = Path(__file__).resolve().parent / "storage" / "temp_workspace"
            target = temp_dir / workspace_id
            if target.resolve().parent != temp_dir.resolve() or not target.is_dir():
                return {'success': False, 'message': 'Invalid workspace identifier.'}
            
            import shutil
            shutil.rmtree(target, ignore_errors=True)
            return {'success': True}
        except (OSError, Exception) as error:
            return {'success': False, 'message': f'Unable to delete working copy: {error}'}

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