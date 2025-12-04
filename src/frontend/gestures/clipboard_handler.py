from PyQt6.QtCore import Qt, QEvent, QPointF
from PyQt6.QtWidgets import QGraphicsView, QGesture, QTapAndHoldGesture, QApplication
from PyQt6.QtGui import QImage
from .base_gesture import BaseGesture

class ClipboardHandler(BaseGesture):
    """
    Handles pasting images from the clipboard using a Tap and Hold gesture.
    """

    def gesture_types(self) -> list[Qt.GestureType]:
        return [Qt.GestureType.TapAndHoldGesture]

    def event_types(self) -> list[QEvent.Type]:
        return []

    def handle_event(self, event: QEvent, view: QGraphicsView) -> bool:
        if event.type() == QEvent.Type.Gesture:
            gesture = event.gesture(Qt.GestureType.TapAndHoldGesture)
            if gesture:
                return self.handle_tap_and_hold(gesture, view)
        return False

    def handle_tap_and_hold(self, gesture: QGesture, view: QGraphicsView) -> bool:
        tap_gesture = gesture
        if not isinstance(tap_gesture, QTapAndHoldGesture):
            return False

        # Trigger when the gesture finishes (user lifts finger/mouse after holding)
        # or when it is triggered (Qt.GestureState.GestureStarted might be better for immediate feedback)
        # Let's use GestureFinished to be safe and avoid multiple triggers, 
        # but for "Tap and Hold" usually the action happens *after* the hold time is met, which is often GestureStarted/Updated.
        # However, to avoid accidental pastes while just resting, let's try GestureFinished first.
        # Actually, standard behavior is usually on "recognition", which is Started.
        # Let's check for GestureFinished to ensure intent.
        
        if tap_gesture.state() == Qt.GestureState.GestureFinished:
            position = tap_gesture.position()
            # Map position to scene coordinates
            scene_pos = view.mapToScene(position.toPoint())
            
            self.paste_image_from_clipboard(view, scene_pos)
            return True
            
        return False

    def paste_image_from_clipboard(self, view: QGraphicsView, pos: QPointF):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                if hasattr(view.scene, 'add_image'):
                    view.scene.add_image(image, pos)
                    print("Image pasted from clipboard.")
                else:
                    print("Error: view.scene does not have add_image method.")
        else:
            print("Clipboard does not contain an image.")
