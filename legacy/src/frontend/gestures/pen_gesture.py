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
        
        # Dispatch to Scene
        if event.type() == QEvent.Type.TabletPress:
            print(pointer_type)
            
            # Determine Tool (Only update on press to prevent switching mid-stroke)
            if not scene.is_drawing:
                if pointer_type == QPointingDevice.PointerType.Eraser:
                    scene.tool = "eraser"
                elif pointer_type == QPointingDevice.PointerType.Pen:
                    if event.button() == Qt.MouseButton.RightButton or (event.buttons() & Qt.MouseButton.RightButton):
                        scene.tool = "lasso"
                    else:
                        scene.tool = "pencil"

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
            if pointer_type == QPointingDevice.PointerType.Eraser:
                print(f"TabletRelease (Eraser): Button={event.button()}, Buttons={event.buttons()}, Modifiers={event.modifiers()}")
            if scene.is_drawing:
                scene.end_stroke(pos, pressure)
                scene.is_drawing = False
            event.accept()
            return True
            
        return False
