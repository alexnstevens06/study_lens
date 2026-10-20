from typing import List, Dict
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QGraphicsView
from .base_gesture import BaseGesture

class GestureManager:
    """
    Manages registration and dispatching of gestures for a QGraphicsView.
    """
    def __init__(self, view: QGraphicsView):
        self.view = view
        self.gesture_handlers: Dict[Qt.GestureType, List[BaseGesture]] = {}
        self.event_handlers: Dict[QEvent.Type, List[BaseGesture]] = {}

    def register_gesture(self, gesture: BaseGesture):
        """
        Registers a gesture handler.
        """
        # Register for Gesture Types
        for g_type in gesture.gesture_types():
            if g_type not in self.gesture_handlers:
                self.gesture_handlers[g_type] = []
                self.view.grabGesture(g_type)
            self.gesture_handlers[g_type].append(gesture)

        # Register for Event Types
        for e_type in gesture.event_types():
            if e_type not in self.event_handlers:
                self.event_handlers[e_type] = []
            self.event_handlers[e_type].append(gesture)

    def dispatch_event(self, event: QEvent) -> bool:
        """
        Dispatches an event to the appropriate registered gesture handlers.
        """
        handled = False
        
        # Handle QGestureEvents
        if event.type() == QEvent.Type.Gesture:
            for gesture_obj in event.gestures():
                g_type = gesture_obj.gestureType()
                if g_type in self.gesture_handlers:
                    for handler in self.gesture_handlers[g_type]:
                        if handler.handle_event(event, self.view):
                            handled = True
            return handled

        # Handle Standard Events
        if event.type() in self.event_handlers:
            for handler in self.event_handlers[event.type()]:
                if handler.handle_event(event, self.view):
                    return True
                    
        return False
