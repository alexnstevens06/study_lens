from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QToolBar
from .base_module import BaseModule

class UndoRedoModule(BaseModule):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.undo_action = None
        self.redo_action = None

    @property
    def priority(self):
        return 10  # High priority, left side

    def get_actions(self):
        # Undo Action
        self.undo_action = QAction("<", self.main_window)
        self.undo_action.setToolTip("Undo (Ctrl+Z)")
        self.undo_action.triggered.connect(self.main_window.pdf_viewer.undo_manager.undo)
        self.undo_action.setEnabled(False) # Initial state

        # Redo Action
        self.redo_action = QAction(">", self.main_window)
        self.redo_action.setToolTip("Redo (Ctrl+Y)")
        self.redo_action.triggered.connect(self.main_window.pdf_viewer.undo_manager.redo)
        self.redo_action.setEnabled(False)

        # Connect to manager signals to update state
        self.main_window.pdf_viewer.undo_manager.canUndoChanged.connect(self.undo_action.setEnabled)
        self.main_window.pdf_viewer.undo_manager.canRedoChanged.connect(self.redo_action.setEnabled)

        return [self.undo_action, self.redo_action]
