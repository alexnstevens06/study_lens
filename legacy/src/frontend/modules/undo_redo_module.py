from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from .base_module import BaseModule

class UndoRedoModule(BaseModule):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.label_counter = None

    @property
    def priority(self):
        return 10  # High priority, left side

    def get_actions(self):
        # Create Container Widget
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        # Buttons
        btn_undo_5 = QPushButton("<<")
        btn_undo = QPushButton("<")
        btn_redo = QPushButton(">")
        btn_redo_5 = QPushButton(">>")
        
        for btn in [btn_undo_5, btn_undo, btn_redo, btn_redo_5]:
            btn.setFixedWidth(30)
            
        # Counter Label
        self.label_counter = QLabel("0 / 0")
        self.label_counter.setContentsMargins(5, 0, 5, 0)
        self.label_counter.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        self.label_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Layout
        layout.addWidget(btn_undo_5)
        layout.addWidget(btn_undo)
        layout.addWidget(self.label_counter)
        layout.addWidget(btn_redo)
        layout.addWidget(btn_redo_5)

        # Connect Buttons
        btn_undo_5.clicked.connect(lambda: self.main_window.pdf_viewer.undo_manager.undo(5))
        btn_undo.clicked.connect(lambda: self.main_window.pdf_viewer.undo_manager.undo(1))
        btn_redo.clicked.connect(lambda: self.main_window.pdf_viewer.undo_manager.redo(1))
        btn_redo_5.clicked.connect(lambda: self.main_window.pdf_viewer.undo_manager.redo(5))

        # Connect Signals for Updates
        self.main_window.pdf_viewer.undo_manager.historyChanged.connect(self.update_ui)
        
        return [container]

    def update_ui(self, current_index, total_count):
        self.label_counter.setText(f"{current_index} / {total_count}")
