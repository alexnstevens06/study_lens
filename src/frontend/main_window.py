import sys
import os
import importlib
import pkgutil
import inspect
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QToolBar
from src.frontend.pdf_viewer import PDFViewer
from src.modules.base_module import BaseModule

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
        self.modules = []
        self.load_modules()

    def load_modules(self):
        # Path to modules directory
        # src/frontend/main_window.py -> src/modules
        modules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')
        
        loaded_modules = []

        # Discover and load modules
        for _, name, _ in pkgutil.iter_modules([modules_path]):
            if name == 'base_module':
                continue
                
            try:
                module = importlib.import_module(f'src.modules.{name}')
                
                # Find BaseModule subclasses
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    
                    if (inspect.isclass(attribute) and 
                        issubclass(attribute, BaseModule) and 
                        attribute is not BaseModule):
                        
                        # Instantiate and initialize
                        instance = attribute(self)
                        instance.init_ui()
                        loaded_modules.append(instance)
                                
            except Exception as e:
                print(f"Failed to load module {name}: {e}")
        
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
