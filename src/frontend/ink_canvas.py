from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPathItem, QGraphicsItem
from PyQt6.QtGui import QPainterPath, QPen, QColor, QImage, QTransform, QPainter
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal

import uuid

class _LiveStrokeItem(QGraphicsItem):
    """Ink stroke while the pen is down.

    Points are stored in a list and each new segment is drawn once into a
    QImage. The graphics view only repaints that segment, instead of copying
    a QPainterPath of the whole stroke on every sample.
    """

    def __init__(self, color, width):
        super().__init__()
        self.color = QColor(color)
        self.pen_width = float(width)
        self._pad = self.pen_width / 2.0 + 1.0
        self.points = []
        self._bounds = QRectF()
        self._origin = QPointF(0, 0)
        self._img = QImage(1, 1, QImage.Format.Format_ARGB32_Premultiplied)
        self._img.fill(Qt.GlobalColor.transparent)

    def boundingRect(self):
        return self._bounds

    def paint(self, painter, option, widget=None):
        painter.drawImage(self._origin, self._img)

    def _pen(self):
        return QPen(
            self.color,
            self.pen_width,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )

    def _to_img(self, pos):
        return QPointF(pos.x() - self._origin.x(), pos.y() - self._origin.y())

    def _ensure(self, pos):
        pad = self._pad + 2.0
        x, y = pos.x(), pos.y()
        left, top = self._origin.x(), self._origin.y()
        right = left + self._img.width()
        bottom = top + self._img.height()
        if left + pad <= x <= right - pad and top + pad <= y <= bottom - pad:
            return
        nleft, ntop, nright, nbottom = left, top, right, bottom
        grow_w = max(self._img.width(), 32)
        grow_h = max(self._img.height(), 32)
        if x - pad < left:
            nleft = x - pad - grow_w
        if y - pad < top:
            ntop = y - pad - grow_h
        if x + pad > right:
            nright = x + pad + grow_w
        if y + pad > bottom:
            nbottom = y + pad + grow_h
        nw = max(int(nright - nleft), self._img.width() * 2, 1)
        nh = max(int(nbottom - ntop), self._img.height() * 2, 1)
        new_img = QImage(nw, nh, QImage.Format.Format_ARGB32_Premultiplied)
        new_img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(new_img)
        painter.drawImage(int(left - nleft), int(top - ntop), self._img)
        painter.end()
        self._img = new_img
        self._origin = QPointF(nleft, ntop)

    def add_point(self, pos):
        pos = QPointF(pos)
        if not self.points:
            self.points.append(pos)
            self._origin = QPointF(pos.x() - 16, pos.y() - 16)
            self._img = QImage(32, 32, QImage.Format.Format_ARGB32_Premultiplied)
            self._img.fill(Qt.GlobalColor.transparent)
            dirty = QRectF(pos.x() - self._pad, pos.y() - self._pad, self._pad * 2, self._pad * 2)
            self.prepareGeometryChange()
            self._bounds = dirty
            painter = QPainter(self._img)
            painter.setPen(self._pen())
            painter.drawPoint(self._to_img(pos))
            painter.end()
            self.update(dirty)
            return
        prev = self.points[-1]
        self.points.append(pos)
        self._ensure(prev)
        self._ensure(pos)
        dirty = QRectF(prev, pos).normalized().adjusted(-self._pad, -self._pad, self._pad, self._pad)
        self.prepareGeometryChange()
        self._bounds = self._bounds.united(dirty)
        painter = QPainter(self._img)
        painter.setPen(self._pen())
        painter.drawLine(self._to_img(prev), self._to_img(pos))
        painter.end()
        self.update(dirty)


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
        self.live_stroke = None
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
            self.live_stroke = _LiveStrokeItem(self.pen_color, self.pen_width)
            uid = str(uuid.uuid4())
            self.live_stroke.setData(Qt.ItemDataRole.UserRole + 1, uid)
            self.live_stroke.add_point(pos)
            self.addItem(self.live_stroke)
            self.current_item = self.live_stroke
            self.current_path = None

        
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

        if self.tool == "pencil" and self.live_stroke is not None:
            self.live_stroke.add_point(pos)
            return

        if self.tool == "lasso" and self.current_path:
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

        if self.tool == "pencil":
            self._commit_live_stroke()

        self.is_drawing = False
        
        if self.tool == "lasso" and self.current_path:
            self.current_path.closeSubpath()
            self.current_item.setPath(self.current_path)
            
            # Construct Selection Operation
            op = Qt.ItemSelectionOperation.ReplaceSelection
            
            # If we already have selected items, we are in Additive Mode
            if self.selected_items_group:
                op = Qt.ItemSelectionOperation.AddToSelection
            else:
                 # If replacing/fresh, ensure we clear any stale state (though clear_selection usually handles this)
                 self.clear_selection()

            # Select items intersecting the path
            self.setSelectionArea(self.current_path, op, Qt.ItemSelectionMode.IntersectsItemShape, QTransform())
            
            # Create selection group from ALL selected items (Old + New)
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



    def _commit_live_stroke(self) -> None:
        """Turn the in-progress image stroke into one path item."""
        live = self.live_stroke
        if live is None:
            return
        points = list(live.points)
        color = QColor(live.color)
        width = live.pen_width
        uid = live.data(Qt.ItemDataRole.UserRole + 1)
        self.removeItem(live)
        self.live_stroke = None

        path = QPainterPath()
        if points:
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        item = self.addPath(path, pen)
        item.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        if uid:
            item.setData(Qt.ItemDataRole.UserRole + 1, uid)
        self.current_path = path
        self.current_item = item

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
                    # Check if item is already saved
                    is_saved = item.data(Qt.ItemDataRole.UserRole + 2) == True
                    
                    strokes.append({
                        "points": points,
                        "color": color_name,
                        "width": item.pen().width(),
                        "id": item.data(Qt.ItemDataRole.UserRole + 1),
                        "saved": is_saved
                    })
        print(f"[DEBUG] get_strokes found {len(strokes)} strokes")
        return strokes

    def mark_strokes_as_saved(self, stroke_ids: list) -> None:
        """Marks the specified strokes as saved in the scene items."""
        if not stroke_ids: return
        
        id_set = set(stroke_ids)
        for item in self.items():
            if isinstance(item, QGraphicsPathItem):
                uid = item.data(Qt.ItemDataRole.UserRole + 1)
                if uid in id_set:
                    item.setData(Qt.ItemDataRole.UserRole + 2, True)

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
                
                # Check if item is already saved
                is_saved = item.data(Qt.ItemDataRole.UserRole + 2) == True
                
                images.append({
                    "image": image,
                    "x": pos.x(),
                    "y": pos.y(),
                    "width": width,
                    "height": height,
                    "id": item.data(Qt.ItemDataRole.UserRole + 1),
                    "saved": is_saved
                })
        return images

    def mark_images_as_saved(self, image_ids: list) -> None:
        """Marks the specified images as saved in the scene items."""
        if not image_ids: return
        
        print(f"[DEBUG] mark_images_as_saved called for IDs: {image_ids}")
        id_set = set(image_ids)
        mapped_count = 0
        for item in self.items():
            from PyQt6.QtWidgets import QGraphicsPixmapItem
            if isinstance(item, QGraphicsPixmapItem):
                uid = item.data(Qt.ItemDataRole.UserRole + 1)
                # print(f"[DEBUG] Checking item {uid}") 
                if uid in id_set:
                    item.setData(Qt.ItemDataRole.UserRole + 2, True)
                    mapped_count += 1
        print(f"[DEBUG] Marked {mapped_count} images as saved.")

    def create_selection_group(self, items: list) -> None:
        if not items:
            return
            
        self.selected_items_group = items
        # self.original_pens = {} # Removed to allow additive updates
        
        # Calculate bounding rect
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for item in items:
            if isinstance(item, QGraphicsPathItem):
                # Save original pen ONLY if not already saved (Additive Logic)
                if item not in self.original_pens:
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
            
            # Remove old selection box if it exists
            if self.selection_box:
                self.removeItem(self.selection_box)
                self.selection_box = None

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
            
            # Restore Saved Status
            if stroke.get("saved", False):
                item.setData(Qt.ItemDataRole.UserRole + 2, True)


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

            # Restore Saved Status
            if img_data.get("saved", False):
                item.setData(Qt.ItemDataRole.UserRole + 2, True)

            self.addItem(item)
