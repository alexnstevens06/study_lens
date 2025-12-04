import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QToolBar, QFileDialog
from PyQt6.QtGui import QAction
from src.frontend.pdf_viewer import PDFViewer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Study Partner")
        self.setGeometry(100, 100, 1000, 800)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Toolbar
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Open Action
        open_action = QAction("Open PDF", self)
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)

        # New Note Action
        new_note_action = QAction("New Note", self)
        new_note_action.triggered.connect(self.new_note)
        toolbar.addAction(new_note_action)

        # Navigation Actions
        prev_action = QAction("Previous", self)
        prev_action.triggered.connect(self.prev_page)
        toolbar.addAction(prev_action)

        next_action = QAction("Next", self)
        next_action.triggered.connect(self.next_page)
        toolbar.addAction(next_action)

        # Close Action
        close_action = QAction("Close", self)
        close_action.triggered.connect(self.close_pdf)
        toolbar.addAction(close_action)

        # PDF Viewer
        self.pdf_viewer = PDFViewer()
        layout.addWidget(self.pdf_viewer)

    def open_pdf(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if file_name:
            self.pdf_viewer.load_document(file_name)

    def new_note(self) -> None:
        self.pdf_viewer.create_blank_document()

    def close_pdf(self) -> None:
        self.pdf_viewer.close_document()

    def prev_page(self) -> None:
        self.pdf_viewer.prev_page()

    def next_page(self) -> None:
        self.pdf_viewer.next_page()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
