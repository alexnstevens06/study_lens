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
        cmd = AddStrokeCommand(scene=self.scene, stroke_data=stroke_data)
        cmd.redo() # Manually execute redo to simulate "doing" it
        self.manager.push(cmd)
        
        self.assertEqual(len(self.scene.items()), initial_count + 1)
        
        # Undo
        self.manager.undo()
        self.assertEqual(len(self.scene.items()), initial_count)
        
        # Redo
        self.manager.redo()
        self.assertEqual(len(self.scene.items()), initial_count + 1)

    def test_multi_step_undo(self):
        # Add 3 strokes
        for i in range(3):
            stroke_data = {
                "points": [(10, 10), (20, 20)],
                "color": "#000000",
                "width": 2.0,
                "id": f"test-uuid-{i}"
            }
            cmd = AddStrokeCommand(self.scene, stroke_data)
            cmd.redo()
            self.manager.push(cmd)
            
        initial_items = len(self.scene.items()) # Should be base + 3
        
        # Undo 2 steps
        self.manager.undo(2)
        # Should simulate removing 2 items, so remaining = initial - 2
        # Base scene items (if any, usually 0 or bg) are not part of undo stack in this simplified test, 
        # but we track relative change.
        
        # We expect 2 items removed
        current_items = len(self.scene.items())
        self.assertEqual(current_items, initial_items - 2)
        
        # Redo 2 steps
        self.manager.redo(2)
        self.assertEqual(len(self.scene.items()), initial_items)

    def test_history_signal(self):
        self.last_history = None
        def on_history(curr, total):
            self.last_history = (curr, total)
        
        self.manager.historyChanged.connect(on_history)
        
        stroke_data = {"points": [], "color": "#000", "width": 1, "id": "1"}
        cmd = AddStrokeCommand(self.scene, stroke_data)
        self.manager.push(cmd)
        
        self.assertEqual(self.last_history, (1, 1))
        
        self.manager.undo()
        self.assertEqual(self.last_history, (0, 1))
        
        self.manager.redo()
        self.assertEqual(self.last_history, (1, 1))

    def test_erase_undo_interaction(self):
        # Regression test for: "elements that have been erased previously are not being undone properly"
        # 1. Add Stroke (ID: A)
        stroke_data = {
            "points": [(0,0), (1,1)],
            "color": "#000",
            "width": 1,
            "id": "item-A"
        }
        cmd_add = AddStrokeCommand(self.scene, stroke_data)
        cmd_add.redo()
        self.manager.push(cmd_add)
        
        # Verify item is there
        self.assertEqual(len(self.scene.items()), 1)
        item_a = self.scene.items()[0]
        
        # 2. Erase Stroke (ID: A) -- Simulate InkCanvas erasing it
        # Real InkCanvas removes the item immediately and emits signal
        self.scene.removeItem(item_a)
        cmd_erase = RemoveStrokeCommand(self.scene, stroke_data)
        self.manager.push(cmd_erase)
        
        self.assertEqual(len(self.scene.items()), 0)
        
        # 3. Undo Erase -> Should restore Item A (as new object A')
        self.manager.undo()
        self.assertEqual(len(self.scene.items()), 1)
        item_a_prime = self.scene.items()[0]
        self.assertNotEqual(item_a, item_a_prime) # It's a new object
        # But ID should match (checked via UserRole logic in real app, mocked here via command)
        
        # 4. Undo Add -> Should remove Item A'
        # This is where it failed previously because cmd_add.item == item_a (which is gone)
        # It needs to find item_a_prime by ID
        self.manager.undo()
        self.assertEqual(len(self.scene.items()), 0)

if __name__ == '__main__':
    unittest.main()
