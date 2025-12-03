from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPathItem, QGraphicsItem
from PyQt6.QtGui import QPainterPath, QPen, QColor, QTabletEvent, QBrush, QInputDevice
from PyQt6.QtCore import Qt, QPointF, QLineF, QRectF, QEvent

class InkCanvas(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path = None
        self.current_item = None
        self.tool = "pencil"  # pencil, eraser, lasso
        self.is_drawing = False
        
        # Pen Settings
        self.pen_color = QColor("black")
        self.pen_width = 2.0
        
        # Lasso Settings
        self.lasso_path = None
        self.lasso_item = None
        
    # Mouse fallback for Stylus (if TabletEvent fails)
    def mousePressEvent(self, event):
        print(f"DEBUG: Scene MousePress Button: {event.button()} Modifiers: {event.modifiers()}")
        if event.button() == Qt.MouseButton.LeftButton:
            self.tool = "pencil"
            self.is_drawing = True
            self.start_stroke(event.scenePos(), 1.0)
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.tool = "eraser"
            self.is_drawing = True
            self.start_stroke(event.scenePos(), 1.0)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.move_stroke(event.scenePos(), 1.0)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_drawing:
            self.end_stroke(event.scenePos(), 1.0)
            self.is_drawing = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def start_stroke(self, pos, pressure):
        if self.tool == "pencil":
            self.current_path = QPainterPath(pos)
            pen = QPen(self.pen_color, self.pen_width * pressure, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            self.current_item = self.addPath(self.current_path, pen)
        
        elif self.tool == "eraser":
            self.erase_at(pos)
            
        elif self.tool == "lasso":
            self.lasso_path = QPainterPath(pos)
            pen = QPen(QColor("blue"), 1.0, Qt.PenStyle.DashLine)
            self.lasso_item = self.addPath(self.lasso_path, pen)

    def move_stroke(self, pos, pressure):
        if self.tool == "pencil" and self.current_path:
            self.current_path.lineTo(pos)
            self.current_item.setPath(self.current_path)
            
        elif self.tool == "eraser":
            self.erase_at(pos)
            
        elif self.tool == "lasso" and self.lasso_path:
            self.lasso_path.lineTo(pos)
            self.lasso_item.setPath(self.lasso_path)

    def end_stroke(self, pos, pressure):
        if self.tool == "pencil":
            self.current_path = None
            self.current_item = None
            
        elif self.tool == "lasso":
            if self.lasso_path:
                self.lasso_path.closeSubpath()
                self.lasso_item.setPath(self.lasso_path)
                self.select_items_in_lasso()
                self.lasso_path = None
                self.lasso_item = None

    def erase_at(self, pos):
        # Reduced eraser radius (4x4)
        eraser_rect = QRectF(pos.x() - 2, pos.y() - 2, 4, 4)
        items = self.items(eraser_rect)
        for item in items:
            if isinstance(item, QGraphicsPathItem) and item != self.lasso_item:
                self.removeItem(item)

    def select_items_in_lasso(self):
        if not self.lasso_path:
            return
        self.clearSelection()
        for item in self.items(self.lasso_path):
            if isinstance(item, QGraphicsPathItem):
                item.setSelected(True)
                pen = item.pen()
                pen.setColor(QColor("red")) # Visual feedback
                item.setPen(pen)
