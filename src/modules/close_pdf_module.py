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
        doc = viewer.get_document()
        
        if doc:
            viewer.save_annotations(save_to_disk=True)
            doc.close()
            viewer.set_document(None)
            viewer.scene.clear()
