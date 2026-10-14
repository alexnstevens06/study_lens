from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QGraphicsView, QSwipeGesture
from .base_gesture import BaseGesture

class SwipeGesture(BaseGesture):
    """
    Handles swipe gestures.
    """
    
    def gesture_types(self) -> list[Qt.GestureType]:
        return [Qt.GestureType.SwipeGesture]

    def event_types(self) -> list[QEvent.Type]:
        return []

    def handle_event(self, event: QEvent, view: QGraphicsView) -> bool:
        gesture = event.gesture(Qt.GestureType.SwipeGesture)
        if gesture:
            # Placeholder for swipe logic
            # In the future, this can emit signals or call methods on the view
            # to trigger navigation.
            
            if gesture.state() == Qt.GestureState.GestureFinished:
                if gesture.horizontalDirection() == QSwipeGesture.SwipeDirection.Left:
                    print("Swipe Left Detected")
                elif gesture.horizontalDirection() == QSwipeGesture.SwipeDirection.Right:
                    print("Swipe Right Detected")
            
            return True
        return False
