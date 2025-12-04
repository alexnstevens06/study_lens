import sys
import os
import importlib
import pkgutil
import inspect
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QToolBar
from src.frontend.pdf_viewer import PDFViewer
from src.frontend.modules.base_module import BaseModule
from src.frontend.config_manager import ConfigManager
from src.frontend.loader_utils import load_classes_from_path
import os

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
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        # PDF Viewer
        self.pdf_viewer = PDFViewer()
        layout.addWidget(self.pdf_viewer)

        # Load Modules
        self.config_manager = ConfigManager()
        self.modules = []
        self.load_modules()

    def load_modules(self):
        # Path to modules directory
        # src/frontend/main_window.py -> src/modules
        modules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')
        
        loaded_modules = []

        # Discover and load modules
        modules_dict = self.config_manager.get_modules()
        
        for file_path, enabled in modules_dict.items():
            if not enabled:
                continue
                
            # Load classes from file
            module_classes = load_classes_from_path(file_path, BaseModule)
            
            for module_class in module_classes:
                try:
                    # Instantiate and initialize
                    instance = module_class(self)
                    instance.init_ui()
                    loaded_modules.append(instance)
                except Exception as e:
                    print(f"Failed to instantiate module from {file_path}: {e}")
        
        # Sort by priority
        loaded_modules.sort(key=lambda x: x.priority)
        
        # Store in instance variable to prevent garbage collection
        self.modules = loaded_modules

        # Add actions to toolbar
        for instance in self.modules:
            actions = instance.get_actions()
            if actions:
                for action in actions:
                    self.toolbar.addAction(action)

    def closeEvent(self, event):
        if self.pdf_viewer.doc:
            self.pdf_viewer.save_annotations(save_to_disk=True)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
