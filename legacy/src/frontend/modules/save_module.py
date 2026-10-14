from PyQt6.QtGui import QAction
from .base_module import BaseModule

class SaveModule(BaseModule):
    @property
    def priority(self):
        return 20 # Priority: Navigation(10) -> Save(20) -> Undo(10?) -> Pen(40) -> Close(50)

    def get_actions(self):
        save_action = QAction("Save", self.main_window)
        save_action.setToolTip("Save Current Changes")
        save_action.triggered.connect(self.save_changes)
        return [save_action]

    def save_changes(self):
        if self.main_window.pdf_viewer.doc:
            self.main_window.pdf_viewer.save_annotations(save_to_disk=True)
            print("[SaveModule] Changes saved manually.")
