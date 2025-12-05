from abc import ABC, abstractmethod
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsPixmapItem
from PyQt6.QtCore import QObject, pyqtSignal, QPointF
from PyQt6.QtGui import QColor, QPen, QTransform
import uuid

class Command(ABC):
    @abstractmethod
    def undo(self):
        pass

    @abstractmethod
    def redo(self):
        pass

class AddStrokeCommand(Command):
    def __init__(self, scene, stroke_data):
        self.scene = scene
        self.stroke_data = stroke_data
        self.stroke_id = stroke_data.get("id")
        self.item = None

    def redo(self):
        # Create and add the stroke
        points = self.stroke_data["points"]
        color = QColor(self.stroke_data["color"])
        width = self.stroke_data["width"]
        
        # We use a helper in scene or recreate logic here? 
        # Better to reuse scene logic or expose a specialized add method.
        # For now, we'll assume scene has a method to add by data or we do it manually.
        # Actually, if we use scene.load_strokes it might be bulk, so let's use a specific single loader or addPath.
        
        from PyQt6.QtGui import QPainterPath
        from PyQt6.QtCore import Qt
        
        path = QPainterPath()
        if points:
            path.moveTo(points[0][0], points[0][1])
            for i in range(1, len(points)):
                path.lineTo(points[i][0], points[i][1])
        
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self.item = self.scene.addPath(path, pen)
        self.item.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        
        # Set ID
        self.item.setData(Qt.ItemDataRole.UserRole + 1, self.stroke_id)

    def undo(self):
        if self.item:
            self.scene.removeItem(self.item)
            self.item = None
        else:
            # Fallback if reference lost: find by ID
            item = self._find_item_by_id(self.stroke_id)
            if item:
                self.scene.removeItem(item)

    def _find_item_by_id(self, uid):
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole + 1) == uid:
                return item
        return None

class RemoveStrokeCommand(Command):
    def __init__(self, scene, stroke_data):
        self.scene = scene
        self.stroke_data = stroke_data
        self.stroke_id = stroke_data.get("id")
        self.item = None # The restored item

    def redo(self):
        # Remove the item
        item = self._find_item_by_id(self.stroke_id)
        if item:
            self.scene.removeItem(item)

    def undo(self):
        # Restore the item (Same logic as AddStrokeCommand.redo)
        points = self.stroke_data["points"]
        color = QColor(self.stroke_data["color"])
        width = self.stroke_data["width"]
        
        from PyQt6.QtGui import QPainterPath, QPen
        from PyQt6.QtCore import Qt
        
        path = QPainterPath()
        if points:
            path.moveTo(points[0][0], points[0][1])
            for i in range(1, len(points)):
                path.lineTo(points[i][0], points[i][1])
        
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self.item = self.scene.addPath(path, pen)
        self.item.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        self.item.setData(Qt.ItemDataRole.UserRole + 1, self.stroke_id)

    def _find_item_by_id(self, uid):
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole + 1) == uid:
                return item
        return None

class AddImageCommand(Command):
    def __init__(self, scene, image_data):
        self.scene = scene
        self.image_data = image_data
        self.image_id = image_data.get("id")
        self.item = None

    def redo(self):
        from PyQt6.QtWidgets import QGraphicsPixmapItem
        from PyQt6.QtGui import QPixmap, QImage
        from PyQt6.QtCore import Qt

        image = self.image_data["image"]
        x = self.image_data["x"]
        y = self.image_data["y"]
        
        pixmap = QPixmap.fromImage(image)
        self.item = QGraphicsPixmapItem(pixmap)
        self.item.setPos(x, y)
        self.item.setFlags(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable | 
                      QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsPixmapItem.GraphicsItemFlag.ItemIsFocusable)
        self.item.setData(Qt.ItemDataRole.UserRole + 1, self.image_id)
        self.scene.addItem(self.item)

    def undo(self):
        item = self._find_item_by_id(self.image_id)
        if item:
            self.scene.removeItem(item)

    def _find_item_by_id(self, uid):
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole + 1) == uid:
                return item
        return None

class MoveItemsCommand(Command):
    def __init__(self, scene, move_data_list):
        """
        move_data_list: List of dicts { "id": uid, "offset": QPointF(dx, dy) }
        """
        self.scene = scene
        self.move_data_list = move_data_list

    def redo(self):
        # Apply offset
        for data in self.move_data_list:
            uid = data["id"]
            offset = data["offset"]
            item = self._find_item_by_id(uid)
            if item:
                if isinstance(item, QGraphicsPathItem):
                   path = item.path()
                   path.translate(offset.x(), offset.y())
                   item.setPath(path)
                else:
                   item.moveBy(offset.x(), offset.y())
        
        # If selection box needs updating, we might need to handle that, 
        # but usually the selection box is rebuilt on click or cleared.
        # Ideally, we clear selection after undo/redo to avoid ghost boxes.
        self.scene.clear_selection()

    def undo(self):
        # Reverse offset
        for data in self.move_data_list:
            uid = data["id"]
            offset = data["offset"]
            item = self._find_item_by_id(uid)
            if item:
                if isinstance(item, QGraphicsPathItem):
                   path = item.path()
                   path.translate(-offset.x(), -offset.y())
                   item.setPath(path)
                else:
                   item.moveBy(-offset.x(), -offset.y())
        self.scene.clear_selection()

    def _find_item_by_id(self, uid):
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole + 1) == uid:
                return item
        return None

class UndoManager(QObject):
    canUndoChanged = pyqtSignal(bool)
    canRedoChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.undo_stack = []
        self.redo_stack = []

    def push(self, command: Command):
        self.undo_stack.append(command)
        self.redo_stack.clear() # New action invalidates redo history
        self.canUndoChanged.emit(True)
        self.canRedoChanged.emit(False)

    def undo(self):
        if not self.undo_stack:
            return
        
        command = self.undo_stack.pop()
        command.undo()
        self.redo_stack.append(command)
        
        self.canUndoChanged.emit(len(self.undo_stack) > 0)
        self.canRedoChanged.emit(True)

    def redo(self):
        if not self.redo_stack:
            return
            
        command = self.redo_stack.pop()
        command.redo()
        self.undo_stack.append(command)
        
        self.canUndoChanged.emit(True)
        self.canRedoChanged.emit(len(self.redo_stack) > 0)

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.canUndoChanged.emit(False)
        self.canRedoChanged.emit(False)
