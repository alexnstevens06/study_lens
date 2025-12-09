from PyQt6.QtGui import QAction
from .base_module import BaseModule

class ClosePDFModule(BaseModule):
    @property
    def priority(self):
        return 50

    def get_actions(self):
        close_action = QAction("Close", self.main_window)
        close_action.triggered.connect(self.close_pdf)
        return [close_action]

    def close_pdf(self):
        viewer = self.main_window.pdf_viewer
        
        # Check if there is a document to save/close
        if viewer.get_document():
            try:
                # Save changes first
                # Note: save_annotations might replace the document object (viewer.doc)
                # so our local reference 'doc' would become stale/closed effectively.
                viewer.save_annotations(save_to_disk=True)
            except Exception as e:
                print(f"[ERROR] Failed to save during close: {e}")
            
            # Re-fetch the current document instance after save
            current_doc = viewer.get_document()
            if current_doc:
                try:
                    current_doc.close()
                except Exception as e:
                    print(f"[WARNING] Error closing document: {e}")
            
            viewer.set_document(None)
            viewer.scene.clear()
