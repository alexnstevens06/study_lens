from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QInputDevice
from PyQt6.QtWidgets import QGraphicsView
from .base_gesture import BaseGesture

class PanGesture(BaseGesture):
    """
    Handles mouse panning (Left Click + Drag).
    """
    
    def __init__(self):
        self._is_panning = False
        self._last_pan_pos = None

    def gesture_types(self) -> list[Qt.GestureType]:
        return []

    def event_types(self) -> list[QEvent.Type]:
        return [
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonRelease
        ]

    def handle_event(self, event: QEvent, view: QGraphicsView) -> bool:
        # Ignore Stylus input (let it pass to PenGesture)
        if hasattr(event, 'device') and event.device().type() == QInputDevice.DeviceType.Stylus:
            return False

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._is_panning = True
                self._last_pan_pos = event.pos()
                view.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return True

        elif event.type() == QEvent.Type.MouseMove:
            if self._is_panning and self._last_pan_pos:
                delta = event.pos() - self._last_pan_pos
                self._last_pan_pos = event.pos()
                
                # Scroll the view
                h_bar = view.horizontalScrollBar()
                v_bar = view.verticalScrollBar()
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
                event.accept()
                return True

        elif event.type() == QEvent.Type.MouseButtonRelease:
            if self._is_panning:
                self._is_panning = False
                view.setCursor(Qt.CursorShape.ArrowCursor)
                event.accept()
                return True
                
        return False
