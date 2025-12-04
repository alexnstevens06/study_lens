from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPathItem
from PyQt6.QtGui import QPainterPath, QPen, QColor, QImage
from PyQt6.QtCore import Qt, QPointF, QRectF

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

    def start_stroke(self, pos: QPointF, pressure: float) -> None:
        self.is_drawing = True
        if self.tool == "pencil":
            self.current_path = QPainterPath(pos)
            #pen = QPen(self.pen_color, self.pen_width * pressure, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            pen = QPen(self.pen_color, self.pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            self.current_item = self.addPath(self.current_path, pen)
        
        elif self.tool == "eraser":
            self.erase_at(pos)

    def move_stroke(self, pos: QPointF, pressure: float) -> None:
        if not self.is_drawing:
            return

        if self.tool == "pencil" and self.current_path:
            self.current_path.lineTo(pos)
            self.current_item.setPath(self.current_path)
            
        elif self.tool == "eraser":
            self.erase_at(pos)

    def end_stroke(self, pos: QPointF, pressure: float) -> None:
        self.is_drawing = False
        if self.tool == "pencil":
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

