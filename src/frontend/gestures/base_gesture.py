from abc import ABC, abstractmethod
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QGraphicsView

class BaseGesture(ABC):
    """
    Abstract base class for all gestures in the modular gesture system.
    """
    
    @abstractmethod
    def gesture_types(self) -> list[Qt.GestureType]:
        """
        Returns a list of Qt GestureTypes that this gesture handles.
        """
        return []

    @abstractmethod
    def event_types(self) -> list[QEvent.Type]:
        """
        Returns a list of QEvent Types that this gesture handles.
        """
        return []

    @abstractmethod
    def handle_event(self, event: QEvent, view: QGraphicsView) -> bool:
        """
        Handles the gesture event.
        
        Args:
            event: The QEvent to handle.
            view: The QGraphicsView instance where the gesture occurred.
            
        Returns:
            bool: True if the event was handled, False otherwise.
        """
        pass
