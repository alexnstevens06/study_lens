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
        
        # Lasso / Selection Settings
        self.lasso_path = None
        self.lasso_item = None
        self.selected_items = []
        self.selection_poly = None  # The closed QPainterPath of the selection
        self.is_moving_selection = False
        self.move_start_pos = None
        self.original_pens = {}  # Store original pens to restore color

    # Mouse fallback removed. Drawing is handled via TabletEvents in PDFViewer.

    def start_stroke(self, pos: QPointF, pressure: float) -> None:
        # 1. Check if we are interacting with an existing selection
        if self.selection_poly and self.selection_poly.contains(pos):
            # User clicked inside the selection -> Start Moving
            self.is_moving_selection = True
            self.move_start_pos = pos
            return

        # 2. If we clicked outside, clear any existing selection
        if self.selected_items:
            self.deselect_items()

        # 3. Proceed with normal tool behavior
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

    def move_stroke(self, pos: QPointF, pressure: float) -> None:
        # 1. Handle Selection Move
        if self.is_moving_selection and self.move_start_pos:
            delta = pos - self.move_start_pos
            
            # Move all selected items
            for item in self.selected_items:
                item.moveBy(delta.x(), delta.y())
            
            # Move the visual lasso boundary
            if self.lasso_item:
                self.lasso_item.moveBy(delta.x(), delta.y())
                
            # Update the selection polygon (for future hit testing)
            self.selection_poly.translate(delta.x(), delta.y())
            
            self.move_start_pos = pos
            return

        # 2. Normal Tool Behavior
        if self.tool == "pencil" and self.current_path:
            self.current_path.lineTo(pos)
            self.current_item.setPath(self.current_path)
            
        elif self.tool == "eraser":
            self.erase_at(pos)
            
        elif self.tool == "lasso" and self.lasso_path:
            self.lasso_path.lineTo(pos)
            self.lasso_item.setPath(self.lasso_path)

    def end_stroke(self, pos: QPointF, pressure: float) -> None:
        if self.is_moving_selection:
            self.is_moving_selection = False
            self.move_start_pos = None
            return

        if self.tool == "pencil":
            self.current_path = None
            self.current_item = None
            
        elif self.tool == "lasso":
            if self.lasso_path:
                self.lasso_path.closeSubpath()
                self.lasso_item.setPath(self.lasso_path)
                self.select_items_in_lasso()
                # Do NOT clear lasso_path/lasso_item here; keep them for the selection state
                # They will be cleared in deselect_items()

    def erase_at(self, pos: QPointF) -> None:
        # Reduced eraser radius (4x4)
        eraser_rect = QRectF(pos.x() - 2, pos.y() - 2, 4, 4)
        items = self.items(eraser_rect)
        for item in items:
            if isinstance(item, QGraphicsPathItem) and item != self.lasso_item:
                self.removeItem(item)
                # If we erased a selected item, remove it from selection list
                if item in self.selected_items:
                    self.selected_items.remove(item)
                    if item in self.original_pens:
                        del self.original_pens[item]

    def select_items_in_lasso(self) -> None:
        if not self.lasso_path:
            return
            
        # Clear any previous selection first (though start_stroke usually handles this)
        if self.selected_items:
            self.deselect_items()
            
        found_items = []
        # Use the path for selection
        for item in self.items(self.lasso_path):
            if isinstance(item, QGraphicsPathItem) and item != self.lasso_item:
                found_items.append(item)
        
        if found_items:
            self.selected_items = found_items
            self.selection_poly = self.lasso_path  # Store the closed path
            
            # Visual Feedback
            for item in self.selected_items:
                self.original_pens[item] = QPen(item.pen()) # Store copy of original pen
                
                new_pen = QPen(item.pen())
                new_pen.setColor(QColor("red"))
                item.setPen(new_pen)
                item.setSelected(True)
        else:
            # If nothing selected, just clear the lasso immediately
            self.deselect_items()

    def deselect_items(self) -> None:
        # Restore original appearance
        for item in self.selected_items:
            if item in self.original_pens:
                item.setPen(self.original_pens[item])
            item.setSelected(False)
            
        self.selected_items.clear()
        self.original_pens.clear()
        self.selection_poly = None
        
        # Remove the visual lasso boundary
        if self.lasso_item:
            self.removeItem(self.lasso_item)
            self.lasso_item = None
        self.lasso_path = None
