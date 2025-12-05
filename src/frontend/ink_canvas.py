from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPathItem
from PyQt6.QtGui import QPainterPath, QPen, QColor, QImage, QTransform
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer

class InkCanvas(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path = None
        self.current_item = None
        self.tool = "pencil"  # pencil, eraser
        self.is_drawing = False
        
        # Pen Settings
        self.pen_color = QColor("black")
        self.pen_width = 2.0

        # Selection State
        self.selected_items_group = []
        self.selection_box = None
        self.original_pens = {}
        self.is_moving_selection = False
        self.move_last_pos = None
        self.deselected_items_in_stroke = set()

    def start_stroke(self, pos: QPointF, pressure: float) -> None:
        # Eraser Logic (Deselect or Erase)
        if self.tool == "eraser":
            self.deselected_items_in_stroke.clear()
            self.process_eraser_at(pos)
            self.is_drawing = True
            return

        # Pen Logic
        if self.tool == "pencil":
            # Check for selection interaction (Move)
            if self.selection_box and self.selection_box.contains(pos):
                self.is_moving_selection = True
                self.move_last_pos = pos
                return
            
            # Clear selection if clicking outside
            if self.selected_items_group:
                self.clear_selection()

        self.is_drawing = True
        if self.tool == "pencil":
            self.current_path = QPainterPath(pos)
            #pen = QPen(self.pen_color, self.pen_width * pressure, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            pen = QPen(self.pen_color, self.pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            self.current_item = self.addPath(self.current_path, pen)
            self.current_item.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        
        elif self.tool == "lasso":
            self.current_path = QPainterPath(pos)
            pen = QPen(self.pen_color, self.pen_width, Qt.PenStyle.DotLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            self.current_item = self.addPath(self.current_path, pen)

        elif self.tool == "eraser":
            self.erase_at(pos)

    def move_stroke(self, pos: QPointF, pressure: float) -> None:
        if self.is_moving_selection and self.move_last_pos:
            delta = pos - self.move_last_pos
            self.selection_box.moveBy(delta.x(), delta.y())
            for item in self.selected_items_group:
                item.moveBy(delta.x(), delta.y())
            self.move_last_pos = pos
            return

        if not self.is_drawing:
            return

        if (self.tool == "pencil" or self.tool == "lasso") and self.current_path:
            self.current_path.lineTo(pos)
            self.current_item.setPath(self.current_path)
            
        elif self.tool == "eraser":
            self.process_eraser_at(pos)

    def end_stroke(self, pos: QPointF, pressure: float) -> None:
        if self.is_moving_selection:
            self.is_moving_selection = False
            return

        self.is_drawing = False
        
        if self.tool == "lasso" and self.current_path:
            self.current_path.closeSubpath()
            self.current_item.setPath(self.current_path)
            # Select items intersecting the path (easier for large objects)
            self.setSelectionArea(self.current_path, Qt.ItemSelectionOperation.ReplaceSelection, Qt.ItemSelectionMode.IntersectsItemShape, QTransform())
            
            # Create selection group from selected items
            items = self.selectedItems()
            self.create_selection_group(items)
            
            # Remove the visual lasso path after a short delay to show closure
            item_to_remove = self.current_item
            QTimer.singleShot(100, lambda: self.fade_out_and_remove(item_to_remove))

        if self.tool == "pencil" or self.tool == "lasso":
            self.current_path = None
            self.current_item = None

    def erase_at(self, pos: QPointF) -> None:
        eraser_rect = QRectF(pos.x() - 2, pos.y() - 2, 4, 4)
        items = self.items(eraser_rect)
        for item in items:
            if isinstance(item, QGraphicsPathItem):
                self.removeItem(item)

    def get_strokes(self) -> list:
        strokes = []
        for item in self.items():
            if isinstance(item, QGraphicsPathItem) and item.path().elementCount() > 0:
                path = item.path()
                points = []
                for i in range(path.elementCount()):
                    elem = path.elementAt(i)
                    points.append((elem.x, elem.y))
                
                if points:
                    strokes.append({
                        "points": points,
                        "color": item.pen().color().name(),
                        "width": item.pen().width()
                    })
        return strokes

    def add_image(self, image: QImage, pos: QPointF = None) -> None:
        from PyQt6.QtWidgets import QGraphicsPixmapItem
        from PyQt6.QtGui import QPixmap
        
        pixmap = QPixmap.fromImage(image)
        item = QGraphicsPixmapItem(pixmap)
        
        if pos:
            # Center the image at the position
            item.setPos(pos.x() - pixmap.width() / 2, pos.y() - pixmap.height() / 2)
            
        item.setFlags(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable | 
                      QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsPixmapItem.GraphicsItemFlag.ItemIsFocusable)
        
        self.addItem(item)

    def get_images(self) -> list:
        images = []
        for item in self.items():
            from PyQt6.QtWidgets import QGraphicsPixmapItem
            if isinstance(item, QGraphicsPixmapItem):
                if item.data(Qt.ItemDataRole.UserRole) == "background":
                    continue
                    
                # Get position
                pos = item.pos()
                
                # Get QImage
                pixmap = item.pixmap()
                image = pixmap.toImage()
                
                # Get dimensions
                width = pixmap.width()
                height = pixmap.height()
                
                images.append({
                    "image": image,
                    "x": pos.x(),
                    "y": pos.y(),
                    "width": width,
                    "height": height
                })
        return images

    def create_selection_group(self, items: list) -> None:
        if not items:
            return
            
        self.selected_items_group = items
        self.original_pens = {}
        
        # Calculate bounding rect
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for item in items:
            if isinstance(item, QGraphicsPathItem):
                # Save original pen
                self.original_pens[item] = QPen(item.pen())
                
                # Set to Red
                new_pen = QPen(item.pen())
                new_pen.setColor(QColor("red"))
                item.setPen(new_pen)
                
                # Update bounds
                rect = item.sceneBoundingRect()
                min_x = min(min_x, rect.left())
                min_y = min(min_y, rect.top())
                max_x = max(max_x, rect.right())
                max_y = max(max_y, rect.bottom())

        # Create Selection Box
        if min_x != float('inf'):
            from PyQt6.QtWidgets import QGraphicsRectItem
            rect = QRectF(min_x - 5, min_y - 5, (max_x - min_x) + 10, (max_y - min_y) + 10)
            self.selection_box = QGraphicsRectItem(rect)
            pen = QPen(QColor("blue"), 1, Qt.PenStyle.DotLine)
            self.selection_box.setPen(pen)
            self.addItem(self.selection_box)

    def clear_selection(self) -> None:
        # Restore original pens
        for item, pen in self.original_pens.items():
            item.setPen(pen)
            
        # Remove selection box
        if self.selection_box:
            self.removeItem(self.selection_box)
            self.selection_box = None
            
        self.selected_items_group = []
        self.original_pens = {}
        self.clearSelection()

    def fade_out_and_remove(self, item) -> None:
        if not item or item.scene() != self:
            return
            
        opacity = item.opacity()
        if opacity <= 0:
            self.removeItem(item)
            return
            
        item.setOpacity(opacity - 0.1)
        QTimer.singleShot(30, lambda: self.fade_out_and_remove(item))

    def process_eraser_at(self, pos: QPointF) -> None:
        # Create a small hit rect
        hit_rect = QRectF(pos.x() - 2, pos.y() - 2, 4, 4)
        items = self.items(hit_rect)
        
        for item in items:
            if isinstance(item, QGraphicsPathItem):
                # If item is selected, deselect it
                if item in self.selected_items_group:
                    # Restore original pen
                    if item in self.original_pens:
                        item.setPen(self.original_pens[item])
                        del self.original_pens[item]
                    
                    self.selected_items_group.remove(item)
                    item.setSelected(False)
                    self.deselected_items_in_stroke.add(item)
                    
                    # Update Selection Box
                    if not self.selected_items_group:
                        self.clear_selection()
                    else:
                        # Recalculate bounds
                        min_x, min_y = float('inf'), float('inf')
                        max_x, max_y = float('-inf'), float('-inf')
                        
                        for sel_item in self.selected_items_group:
                            rect = sel_item.sceneBoundingRect()
                            min_x = min(min_x, rect.left())
                            min_y = min(min_y, rect.top())
                            max_x = max(max_x, rect.right())
                            max_y = max(max_y, rect.bottom())
                            
                        if self.selection_box:
                            rect = QRectF(min_x - 5, min_y - 5, (max_x - min_x) + 10, (max_y - min_y) + 10)
                            self.selection_box.setRect(rect)
                
                # If item is NOT selected (and not the selection box itself), erase it
                elif item != self.selection_box:
                     if item not in self.deselected_items_in_stroke:
                         self.removeItem(item)

    def erase_at(self, pos: QPointF) -> None:
        # Kept for compatibility if needed, but process_eraser_at handles both
        self.process_eraser_at(pos)

