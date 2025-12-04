from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QPointingDevice
from PyQt6.QtWidgets import QGraphicsView
from .base_gesture import BaseGesture

class PenGesture(BaseGesture):
    """
    Handles pen input for drawing on the InkCanvas.
    """
    
    def gesture_types(self) -> list[Qt.GestureType]:
        return []

    def event_types(self) -> list[QEvent.Type]:
        return [
            QEvent.Type.TabletPress,
            QEvent.Type.TabletMove,
            QEvent.Type.TabletRelease
        ]

    def handle_event(self, event: QEvent, view: QGraphicsView) -> bool:
        # Ensure we have access to the scene and it's an InkCanvas (or has compatible interface)
        if not hasattr(view, 'scene') or not hasattr(view.scene, 'is_drawing'):
            return False
            
        scene = view.scene
        pos = view.mapToScene(event.position().toPoint())
        pressure = event.pressure()
        pointer_type = event.pointerType()
        
        # Determine Tool (Only update if not currently drawing to prevent switching mid-stroke)
        if not scene.is_drawing:
            if pointer_type == QPointingDevice.PointerType.Eraser:
                scene.tool = "eraser"
            else:
                scene.tool = "pencil"

        # Dispatch to Scene
        if event.type() == QEvent.Type.TabletPress:
            # print("[DEBUG] TabletPress received")
            scene.is_drawing = True
            scene.start_stroke(pos, pressure)
            event.accept()
            return True
            
        elif event.type() == QEvent.Type.TabletMove:
            if scene.is_drawing:
                scene.move_stroke(pos, pressure)
                event.accept()
                return True
                
        elif event.type() == QEvent.Type.TabletRelease:
            # print("[DEBUG] TabletRelease received")
            if scene.is_drawing:
                scene.end_stroke(pos, pressure)
                scene.is_drawing = False
            event.accept()
            return True
            
        return False
