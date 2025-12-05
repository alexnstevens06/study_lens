from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPathItem
from PyQt6.QtGui import QPainterPath, QPen, QColor, QImage, QTransform
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal

import uuid

class InkCanvas(QGraphicsScene):
    strokeCreated = pyqtSignal(dict)
    strokeErased = pyqtSignal(dict) # Emits the stroke DATE of the erased item
    itemsMoved = pyqtSignal(list) # List of {id, offset}
    imageAdded = pyqtSignal(dict)
    imageMoved = pyqtSignal(dict)

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
        self.is_moving_selection = False
        self.move_last_pos = None
        self.deselected_items_in_stroke = set()
        self.erased_items_in_stroke = [] # Track erased items specifically for undo
        self.start_move_offsets = {} # Track initial positions for move undo


    def start_stroke(self, pos: QPointF, pressure: float) -> None:
        # Eraser Logic (Deselect or Erase)
        if self.tool == "eraser":
            self.deselected_items_in_stroke.clear()
            self.erased_items_in_stroke = []
            self.process_eraser_at(pos)
            self.is_drawing = True
            return

        # Pen Logic
        if self.tool == "pencil":
            # Check for selection interaction (Move)
            if self.selection_box and self.selection_box.contains(pos):
                self.is_moving_selection = True
                self.move_last_pos = pos
                
                # Capture start positions for undo
                self.start_move_offsets = {}
                for item in self.selected_items_group:
                    uid = item.data(Qt.ItemDataRole.UserRole + 1)
                    if uid:
                        self.start_move_offsets[uid] = item.pos() # Should be (0,0) usually due to baking, but good to be safe
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
            
            # Assign UUID
            uid = str(uuid.uuid4())
            self.current_item.setData(Qt.ItemDataRole.UserRole + 1, uid)

        
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
            
            # Calculate total move delta for undo
            move_data = []
            for item in self.selected_items_group:
                uid = item.data(Qt.ItemDataRole.UserRole + 1)
                if uid:
                     # Since we bake the move, the 'offset' is effectively the change in path translation.
                     # But wait, bake_selection_move modifies the path in place and resets pos to 0,0.
                     # So we need to capture the change BEFORE baking? 
                     # Actually, bake relies on item.pos().
                     offset = item.pos()
                     if not offset.isNull():
                         move_data.append({"id": uid, "offset": offset})

            self.bake_selection_move()
            
            if move_data:
                self.itemsMoved.emit(move_data)
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
            if self.tool == "pencil" and self.current_item:
                 # Emit Creation Signal
                 uid = self.current_item.data(Qt.ItemDataRole.UserRole + 1)
                 # elementAt returns QPainterPath.Element which has properties x and y (floats), not methods
                 points = []
                 for i in range(self.current_path.elementCount()):
                     elem = self.current_path.elementAt(i)
                     points.append((elem.x, elem.y))

                 stroke_data = {
                     "points": points,
                     "color": self.current_item.pen().color().name(QColor.NameFormat.HexArgb),
                     "width": self.current_item.pen().width(),
                     "id": uid
                 }
                 self.strokeCreated.emit(stroke_data)

            self.current_path = None
            self.current_item = None
            
        elif self.tool == "eraser":
            # Emit Erase Signal for all items erased in this stroke
             for item_data in self.erased_items_in_stroke:
                 self.strokeErased.emit(item_data)
             self.erased_items_in_stroke = []


    def erase_at(self, pos: QPointF) -> None:
        eraser_rect = QRectF(pos.x() - 2, pos.y() - 2, 4, 4)
        items = self.items(eraser_rect)
        for item in items:
            if isinstance(item, QGraphicsPathItem):
                self.removeItem(item)

    def get_strokes(self) -> list:
        strokes = []
        # items() returns items in descending stacking order (top-most first).
        # We want to save them in creation order (bottom-most first), so we reverse the list.
        items = list(self.items())
        items.reverse()
        
        for item in items:
            if isinstance(item, QGraphicsPathItem) and item.path().elementCount() > 0:
                path = item.path()
                points = []
                for i in range(path.elementCount()):
                    elem = path.elementAt(i)
                    points.append((elem.x, elem.y))
                
                if points:
                    color_name = item.pen().color().name(QColor.NameFormat.HexArgb)
                    strokes.append({
                        "points": points,
                        "color": color_name,
                        "width": item.pen().width(),
                        "id": item.data(Qt.ItemDataRole.UserRole + 1)
                    })
        print(f"[DEBUG] get_strokes found {len(strokes)} strokes")
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
        
        # Assign UUID
        uid = str(uuid.uuid4())
        item.setData(Qt.ItemDataRole.UserRole + 1, uid)

        self.addItem(item)
        
        # Emit Signal
        image_data = {
             "image": image,
             "x": item.pos().x(),
             "y": item.pos().y(),
             "width": pixmap.width(),
             "height": pixmap.height(),
             "id": uid
        }
        self.imageAdded.emit(image_data)


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
                    "height": height,
                    "id": item.data(Qt.ItemDataRole.UserRole + 1)
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
                          # Capture data before removing
                          if isinstance(item, QGraphicsPathItem):
                               path = item.path()
                               points = []
                               for i in range(path.elementCount()):
                                   elem = path.elementAt(i)
                                   points.append((elem.x, elem.y))
                               
                               uid = item.data(Qt.ItemDataRole.UserRole + 1)
                               stroke_data = {
                                   "points": points,
                                   "color": item.pen().color().name(QColor.NameFormat.HexArgb),
                                   "width": item.pen().width(),
                                   "id": uid
                               }
                               self.erased_items_in_stroke.append(stroke_data)

                          self.removeItem(item)

    def erase_at(self, pos: QPointF) -> None:
        # Kept for compatibility if needed, but process_eraser_at handles both
        self.process_eraser_at(pos)

    def bake_selection_move(self) -> None:
        """
        Bakes the current item position into the path data and resets position to (0,0).
        This ensures that get_strokes() returns the correct coordinates.
        """
        if not self.selected_items_group:
            return
            
        for item in self.selected_items_group:
            if isinstance(item, QGraphicsPathItem):
                # Get the current offset
                offset = item.pos()
                if offset.isNull():
                    continue
                    
                # Apply offset to path
                path = item.path()
                path.translate(offset.x(), offset.y())
                item.setPath(path)
                
                # Reset item position
                item.setPos(0, 0)
                
        # Also update selection box if it exists
        if self.selection_box:
             offset = self.selection_box.pos()
             if not offset.isNull():
                 rect = self.selection_box.rect()
                 rect.translate(offset.x(), offset.y())
                 self.selection_box.setRect(rect)
                 self.selection_box.setPos(0, 0)

    def load_strokes(self, strokes: list) -> None:
        for stroke in strokes:
            points = stroke["points"]
            if not points:
                continue
                
            path = QPainterPath()
            path.moveTo(points[0][0], points[0][1])
            for i in range(1, len(points)):
                path.lineTo(points[i][0], points[i][1])
                
            color = QColor(stroke["color"])
            width = stroke["width"]
            
            pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            item = self.addPath(path, pen)
            item.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
            
            # Restore UUID
            if "id" in stroke:
                item.setData(Qt.ItemDataRole.UserRole + 1, stroke["id"])
            else:
                # Assign new ID if missing (legacy support)
                item.setData(Qt.ItemDataRole.UserRole + 1, str(uuid.uuid4()))


    def load_images(self, images: list) -> None:
        from PyQt6.QtWidgets import QGraphicsPixmapItem
        from PyQt6.QtGui import QPixmap
        
        for img_data in images:
            image = img_data["image"]
            x = img_data["x"]
            y = img_data["y"]
            
            pixmap = QPixmap.fromImage(image)
            item = QGraphicsPixmapItem(pixmap)
            item.setPos(x, y)
            
            item.setFlags(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable | 
                          QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable | 
                          QGraphicsPixmapItem.GraphicsItemFlag.ItemIsFocusable)
            
            # Restore UUID
            if "id" in img_data:
                item.setData(Qt.ItemDataRole.UserRole + 1, img_data["id"])
            else:
                 item.setData(Qt.ItemDataRole.UserRole + 1, str(uuid.uuid4()))

            self.addItem(item)
