import sys
import os
from PyQt6.QtCore import QPointF, QEvent, Qt, QSize
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsPathItem
from PyQt6.QtGui import QPen, QColor, QPainterPath, QMouseEvent

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.frontend.ink_canvas import InkCanvas
from src.frontend.gestures.pan_gesture import PanGesture

def test_touch_move_deselect():
    app = QApplication([])
    canvas = InkCanvas()
    view = QGraphicsView(canvas)
    view.resize(800, 600)
    pan_gesture = PanGesture()
    
    # 1. Add item and select it
    path = QPainterPath()
    path.addRect(20, 20, 40, 40)
    item = canvas.addPath(path, QPen(QColor("black"), 2))
    item.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
    
    # Manually trigger selection
    canvas.create_selection_group([item])
    
    if item.pen().color().name() == "#ff0000":
        print("PASS: Item selected (Red).")
    else:
        print("FAIL: Item not selected.")
        
    # 2. Test Touch Move (via PanGesture)
    # Simulate Mouse Press inside selection box (approx 20,20 to 60,60)
    # View coordinates map to scene coordinates 1:1 initially if not scrolled
    
    class MockMouseEvent:
        def __init__(self, type, pos, button):
            self._type = type
            self._pos = pos
            self._button = button
        def type(self): return self._type
        def pos(self): return self._pos
        def button(self): return self._button
        def accept(self): pass
        
    # Press at 40, 40
    press_event = MockMouseEvent(QEvent.Type.MouseButtonPress, QPointF(40, 40).toPoint(), Qt.MouseButton.LeftButton)
    if pan_gesture.handle_event(press_event, view):
        print("PASS: PanGesture handled press inside selection.")
    else:
        print("FAIL: PanGesture ignored press inside selection.")
        
    # Move to 50, 50
    move_event = MockMouseEvent(QEvent.Type.MouseMove, QPointF(50, 50).toPoint(), Qt.MouseButton.NoButton)
    pan_gesture.handle_event(move_event, view)
    
    # Release
    release_event = MockMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(50, 50).toPoint(), Qt.MouseButton.LeftButton)
    pan_gesture.handle_event(release_event, view)
    
    # Check item position
    if item.pos().x() == 10 and item.pos().y() == 10:
        print("PASS: Item moved by touch.")
    else:
        print(f"FAIL: Item not moved correctly. Pos: {item.pos()}")
        
    # 3. Test Pen Deselect (via InkCanvas methods directly)
    # Simulate Pen Stroke over the item (now at 30,30 to 70,70)
    canvas.tool = "pencil"
    canvas.start_stroke(QPointF(40, 40), 1.0) # Should hit item
    
    if item.pen().color().name() == "#000000":
        print("PASS: Item deselected (Black).")
    else:
        print(f"FAIL: Item not deselected. Color: {item.pen().color().name()}")
        
    if not canvas.selected_items_group:
        print("PASS: Selection group empty.")
    else:
        print("FAIL: Selection group not empty.")

if __name__ == "__main__":
    try:
        test_touch_move_deselect()
    except Exception as e:
        print(f"Test Failed: {e}")
