from PyQt6.QtGui import QAction
from .base_module import BaseModule

class NewNoteModule(BaseModule):
    @property
    def priority(self):
        return 20

    def get_actions(self):
        new_note_action = QAction("New Note", self.main_window)
        new_note_action.triggered.connect(self.new_note)
        return [new_note_action]

    def new_note(self):
        import fitz
        doc = fitz.open()
        # A4 size: 595 x 842 points
        doc.new_page(width=595, height=842)
        self.main_window.pdf_viewer.set_document(doc, is_new_file=True)
