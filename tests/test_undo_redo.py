import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF
from src.frontend.ink_canvas import InkCanvas
from src.frontend.undo_manager import UndoManager, AddStrokeCommand, RemoveStrokeCommand

# Hack to allow QApp in tests
app = QApplication([])

class TestUndoRedo(unittest.TestCase):
    def setUp(self):
        self.scene = InkCanvas()
        self.manager = UndoManager()
        
        # Connect signals for manual testing simulation
        self.scene.strokeCreated.connect(lambda data: self.manager.push(AddStrokeCommand(self.scene, data)))
        self.scene.strokeErased.connect(lambda data: self.manager.push(RemoveStrokeCommand(self.scene, data)))

    def test_add_undo_redo_stroke(self):
        # Simulator adding a stroke
        stroke_data = {
            "points": [(10, 10), (20, 20)],
            "color": "#000000",
            "width": 2.0,
            "id": "test-uuid-1"
        }
        
        # Determine initial count
        initial_count = len(self.scene.items())
        
        # Execute "Add"
        cmd = AddStrokeCommand(self.scene, stroke_data)
        cmd.redo() # Manually execute redo to simulate "doing" it
        self.manager.push(cmd)
        
        self.assertEqual(len(self.scene.items()), initial_count + 1)
        
        # Undo
        self.manager.undo()
        self.assertEqual(len(self.scene.items()), initial_count)
        
        # Redo
        self.manager.redo()
        self.assertEqual(len(self.scene.items()), initial_count + 1)

if __name__ == '__main__':
    unittest.main()
