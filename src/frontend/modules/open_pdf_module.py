from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFileDialog
from .base_module import BaseModule

class OpenPDFModule(BaseModule):
    @property
    def priority(self):
        return 10

    def get_actions(self):
        open_action = QAction("Open PDF", self.main_window)
        open_action.triggered.connect(self.open_pdf)
        return [open_action]

    def open_pdf(self):
        file_name, _ = QFileDialog.getOpenFileName(self.main_window, "Open PDF", "", "PDF Files (*.pdf)")
        if file_name:
            import fitz
            try:
                doc = fitz.open(file_name)
                self.main_window.pdf_viewer.set_document(doc)
            except Exception as e:
                print(f"Error loading document: {e}")
