import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication, QGraphicsPathItem
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPainterPath, QPen, QColor

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.frontend.ink_canvas import InkCanvas

class TestLassoUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.canvas = InkCanvas()
        
    def test_move_stroke_updates_data(self):
        # 1. Create a stroke
        self.canvas.tool = "pencil"
        self.canvas.start_stroke(QPointF(10, 10), 1.0)
        self.canvas.move_stroke(QPointF(20, 20), 1.0)
        self.canvas.end_stroke(QPointF(20, 20), 1.0)
        
        # Get the item
        items = [i for i in self.canvas.items() if isinstance(i, QGraphicsPathItem)]
        self.assertEqual(len(items), 1)
        item = items[0]
        
        # Verify initial position
        self.assertEqual(item.pos(), QPointF(0, 0))
        
        # 2. Select it (Simulate Lasso)
        # We can manually select it for the test
        self.canvas.create_selection_group([item])
        self.assertTrue(item in self.canvas.selected_items_group)
        self.assertIsNotNone(self.canvas.selection_box)
        
        # 3. Move it
        # Simulate mouse interaction on selection box
        # start_stroke checks for selection_box contains
        center = self.canvas.selection_box.sceneBoundingRect().center()
        self.canvas.tool = "pencil" # Tool must be pencil to move selection
        
        self.canvas.start_stroke(center, 1.0)
        self.assertTrue(self.canvas.is_moving_selection)
        
        # Move by (100, 100)
        self.canvas.move_stroke(center + QPointF(100, 100), 1.0)
        self.canvas.end_stroke(center + QPointF(100, 100), 1.0)
        
        # 4. Check get_strokes
        strokes = self.canvas.get_strokes()
        self.assertEqual(len(strokes), 1)
        points = strokes[0]['points']
        
        # The first point was (10, 10). After moving 100, 100, it should be (110, 110)
        first_point = points[0]
        print(f"Original Point: (10, 10)")
        print(f"Moved Amount: (100, 100)")
        print(f"Result Point: {first_point}")
        
        # This assertion is expected to FAIL currently
        self.assertAlmostEqual(first_point[0], 110.0, delta=1.0)
        self.assertAlmostEqual(first_point[1], 110.0, delta=1.0)

if __name__ == '__main__':
    unittest.main()
