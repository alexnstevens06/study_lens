from abc import ABC, abstractmethod
from PyQt6.QtWidgets import QMainWindow, QToolBar
from typing import List, Any

class BaseModule(ABC):
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window

    @abstractmethod
    def get_actions(self) -> List[Any]:
        """
        Returns a list of QAction objects or QWidgets to be added to the toolbar.
        """
        pass

    @property
    def priority(self) -> int:
        """
        Returns the priority of the module. Lower numbers appear first in the toolbar.
        Default is 100.
        """
        return 100

    def init_ui(self):
        """
        Optional method to perform additional UI initialization.
        """
        pass
