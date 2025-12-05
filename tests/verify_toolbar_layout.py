import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication, QWidget, QSizePolicy, QToolBar

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.frontend.main_window import MainWindow
from src.frontend.modules.navigation_module import NavigationModule
from src.frontend.modules.open_pdf_module import OpenPDFModule

class TestToolbarLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.window = MainWindow()
        # Force load modules if not already loaded (MainWindow calls it in __init__)
        
    def test_navigation_module_size_policy(self):
        # Find the navigation module instance
        nav_module = next((m for m in self.window.modules if isinstance(m, NavigationModule)), None)
        self.assertIsNotNone(nav_module, "NavigationModule not loaded")
        
        # Get the container widget from the toolbar
        # We need to find the action that corresponds to the container
        # Since get_actions returns [container], we can check the toolbar's actions
        
        # Alternatively, we can just check the result of get_actions directly for this test
        actions = nav_module.get_actions()
        self.assertEqual(len(actions), 1)
        container = actions[0]
        self.assertIsInstance(container, QWidget)
        
        policy = container.sizePolicy()
        self.assertEqual(policy.horizontalPolicy(), QSizePolicy.Policy.Fixed, "Navigation container should have Fixed horizontal policy")

    def test_module_order(self):
        # Check if OpenPDF is before Navigation
        modules = self.window.modules
        open_pdf_idx = -1
        nav_idx = -1
        
        for i, m in enumerate(modules):
            if isinstance(m, OpenPDFModule):
                open_pdf_idx = i
            elif isinstance(m, NavigationModule):
                nav_idx = i
                
        self.assertNotEqual(open_pdf_idx, -1, "OpenPDFModule not found")
        self.assertNotEqual(nav_idx, -1, "NavigationModule not found")
        self.assertLess(open_pdf_idx, nav_idx, "OpenPDFModule should be before NavigationModule")

    def tearDown(self):
        self.window.close()

if __name__ == '__main__':
    unittest.main()
