from PyQt6.QtGui import QAction
from .base_module import BaseModule

class NavigationModule(BaseModule):
    @property
    def priority(self):
        return 30

    def get_actions(self):
        prev_action = QAction("Previous", self.main_window)
        prev_action.triggered.connect(self.prev_page)
        
        next_action = QAction("Next", self.main_window)
        next_action.triggered.connect(self.next_page)
        
        return [prev_action, next_action]

    def prev_page(self):
        viewer = self.main_window.pdf_viewer
        doc = viewer.get_document()
        current_page = viewer.get_page()
        
        if doc and current_page > 0:
            viewer.save_annotations(save_to_disk=False)
            viewer.set_page(current_page - 1)

    def next_page(self):
        viewer = self.main_window.pdf_viewer
        doc = viewer.get_document()
        current_page = viewer.get_page()
        
        if not doc: return
        
        viewer.save_annotations(save_to_disk=False)
        
        if current_page < len(doc) - 1:
            viewer.set_page(current_page + 1)
        else:
            # Infinite Scroll: Add new page
            doc.new_page(width=595, height=842)
            viewer.set_page(current_page + 1)
