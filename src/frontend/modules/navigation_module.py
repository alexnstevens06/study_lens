from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLineEdit, QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from .base_module import BaseModule

class NavigationModule(BaseModule):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.input_field = None
        self.total_label = None

    @property
    def priority(self) -> int:
        return 10  # High priority to appear early (left)

    def get_actions(self):
        # Create Container Widget
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Set Fixed Size Policy to prevent expansion
        container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        
        # Buttons
        btn_prev_5 = QPushButton("<<")
        btn_prev = QPushButton("<")
        btn_next = QPushButton(">")
        btn_next_5 = QPushButton(">>")
        
        for btn in [btn_prev_5, btn_prev, btn_next, btn_next_5]:
            btn.setFixedWidth(30)
        
        # Input
        self.input_field = QLineEdit()
        self.input_field.setFixedWidth(40)
        self.input_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_field.returnPressed.connect(self.on_input_return)
        
        # Label
        self.total_label = QLabel("/ 0")
        self.total_label.setContentsMargins(5, 0, 5, 0)
        # Prevent label from expanding
        self.total_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        # Add to layout
        layout.addWidget(btn_prev_5)
        layout.addWidget(btn_prev)
        layout.addWidget(self.input_field)
        layout.addWidget(self.total_label)
        layout.addWidget(btn_next)
        layout.addWidget(btn_next_5)

        # Connect Signals
        btn_prev_5.clicked.connect(lambda: self.change_page(-5))
        btn_prev.clicked.connect(lambda: self.change_page(-1))
        btn_next.clicked.connect(lambda: self.change_page(1))
        btn_next_5.clicked.connect(lambda: self.change_page(5))
        
        # Connect to PDFViewer Signals
        self.main_window.pdf_viewer.document_changed.connect(self.update_ui)
        self.main_window.pdf_viewer.page_changed.connect(lambda _: self.update_ui())
        
        # Initial Update
        self.update_ui()

        return [container]

    def change_page(self, delta: int):
        if not self.main_window.pdf_viewer.doc:
            return
            
        current = self.main_window.pdf_viewer.get_page()
        self.go_to_page(current + delta)

    def on_input_return(self):
        text = self.input_field.text()
        try:
            # Handle float (round to nearest)
            page_num = int(round(float(text)))
            # Convert 1-based input to 0-based index
            self.go_to_page(page_num - 1)
        except ValueError:
            # Invalid input, reset to current
            self.update_ui()

    def go_to_page(self, page_index: int):
        if not self.main_window.pdf_viewer.doc:
            return
            
        total_pages = self.main_window.pdf_viewer.doc.page_count
        
        # Auto-add page if navigating past end
        if page_index >= total_pages:
            self.main_window.pdf_viewer.add_new_page()
            self.update_ui()
            return

        # Handle bounds
        if page_index < 0:
            page_index = 0
            
        self.main_window.pdf_viewer.set_page(page_index)
        self.update_ui()

    def update_ui(self):
        if not self.main_window.pdf_viewer.doc:
            self.input_field.setText("0")
            self.total_label.setText("/ 0")
            self.input_field.setEnabled(False)
            return
            
        current = self.main_window.pdf_viewer.get_page()
        total = self.main_window.pdf_viewer.doc.page_count
        
        self.input_field.setEnabled(True)
        # Display as 1-based
        self.input_field.setText(str(current + 1))
        self.total_label.setText(f"/ {total}")
