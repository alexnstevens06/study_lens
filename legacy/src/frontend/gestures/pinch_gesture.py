from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QGraphicsView, QPinchGesture
from .base_gesture import BaseGesture

class PinchGesture(BaseGesture):
    """
    Handles pinch-to-zoom gestures.
    """
    
    def gesture_types(self) -> list[Qt.GestureType]:
        return [Qt.GestureType.PinchGesture]

    def event_types(self) -> list[QEvent.Type]:
        return []

    def handle_event(self, event: QEvent, view: QGraphicsView) -> bool:
        gesture = event.gesture(Qt.GestureType.PinchGesture)
        if gesture:
            change_flags = gesture.changeFlags()
            if change_flags & QPinchGesture.ChangeFlag.ScaleFactorChanged:
                scale_factor = gesture.scaleFactor()
                view.scale(scale_factor, scale_factor)
            return True
        return False
