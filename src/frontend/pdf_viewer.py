import fitz  # PyMuPDF
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPinchGesture, QSwipeGesture, QScroller, QScrollerProperties
from PyQt6.QtGui import QPixmap, QImage, QInputDevice, QPointingDevice, QColor
from PyQt6.QtCore import Qt, QEvent
from src.frontend.gestures.base_gesture import BaseGesture
from src.config_manager import ConfigManager
from src.loader_utils import load_classes_from_path
from src.frontend.ink_canvas import InkCanvas
from src.frontend.gestures.gesture_manager import GestureManager
import os
from datetime import datetime

class PDFViewer(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = InkCanvas(self)
        self.setScene(self.scene)
        self.doc = None
        self.current_page_num = 0
        self.is_new_file = False
        
        # Optimization: Render at a reasonable scale
        self.zoom_level = 2.0  # 2.0 = 144 DPI (High Quality)
        
        # Enable Gestures via Manager
        self.gesture_manager = GestureManager(self)
        self.config_manager = ConfigManager()
        
        gestures_dict = self.config_manager.get_gestures()
        for file_path, enabled in gestures_dict.items():
            if not enabled:
                continue
                
            gesture_classes = load_classes_from_path(file_path, BaseGesture)
            for gesture_class in gesture_classes:
                try:
                    self.gesture_manager.register_gesture(gesture_class())
                except Exception as e:
                    print(f"Failed to register gesture from {file_path}: {e}")
        
        # Enable Kinetic Scrolling (Touch to Pan)
        QScroller.grabGesture(self.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        scroller = QScroller.scroller(self.viewport())
        props = scroller.scrollerProperties()
        
        # Tune properties for better feel
        props.setScrollMetric(QScrollerProperties.ScrollMetric.DragStartDistance, 0.001)
        props.setScrollMetric(QScrollerProperties.ScrollMetric.OvershootDragResistanceFactor, 0.5)
        props.setScrollMetric(QScrollerProperties.ScrollMetric.OvershootScrollDistanceFactor, 0.5)
        props.setScrollMetric(QScrollerProperties.ScrollMetric.SnapTime, 0.5)
        scroller.setScrollerProperties(props)
        
        # UI Polish
        self.setDragMode(QGraphicsView.DragMode.NoDrag)  # Disable built-in drag to allow pen drawing
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        

    def set_document(self, doc, is_new_file: bool = False) -> None:
        self.doc = doc
        self.is_new_file = is_new_file
        self.current_page_num = 0
        self.render_page()

    def get_document(self):
        return self.doc

    def set_page(self, page_num: int) -> None:
        self.current_page_num = page_num
        self.render_page()

    def get_page(self) -> int:
        return self.current_page_num

    def refresh_view(self) -> None:
        self.render_page()

    def render_page(self) -> None:
        if not self.doc:
            return

        try:
            page = self.doc.load_page(self.current_page_num)
        except Exception as e:
            print(f"Error loading page {self.current_page_num}: {e}")
            return
        
        # Render page to image
        mat = fitz.Matrix(self.zoom_level, self.zoom_level)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to QImage
        img_format = QImage.Format.Format_RGB888
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, img_format)
        
        # Convert to QPixmap and add to scene
        pixmap = QPixmap.fromImage(img)
        
        self.scene.clear()
        self.scene.addPixmap(pixmap)
        self.setSceneRect(0, 0, pix.width, pix.height)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Gesture:
            return self.gesture_manager.dispatch_event(event)
        return super().event(event)

    def viewportEvent(self, event: QEvent) -> bool:
        if self.gesture_manager.dispatch_event(event):
            return True
        return super().viewportEvent(event)

    def mousePressEvent(self, event: QEvent) -> None:
        if self.gesture_manager.dispatch_event(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QEvent) -> None:
        if self.gesture_manager.dispatch_event(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QEvent) -> None:
        if self.gesture_manager.dispatch_event(event):
            return
        super().mouseReleaseEvent(event)

    def save_annotations(self, save_to_disk: bool = True) -> None:
        if not self.doc: return
        
        page = self.doc.load_page(self.current_page_num)
        strokes = self.scene.get_strokes()
        
        for stroke in strokes:
            points = stroke["points"]
            if len(points) < 2: continue
            
            # Convert scene points to PDF coordinates
            pdf_points = []
            for x, y in points:
                pdf_points.append((x / self.zoom_level, y / self.zoom_level))
                
            annot = page.add_ink_annot([pdf_points])
            
            # Parse color
            try:
                qcolor = QColor(stroke["color"])
                if not qcolor.isValid():
                    print(f"[ERROR] Invalid color: {stroke['color']}")
                    rgb = (0, 0, 0) # Default to black
                else:
                    rgb = (qcolor.redF(), qcolor.greenF(), qcolor.blueF())
                
                annot.set_colors(stroke=rgb)
            except Exception as e:
                print(f"[ERROR] Failed to set color: {e}, stroke color data: {stroke.get('color')}")
                annot.set_colors(stroke=(0, 0, 0)) # Fallback
                
            annot.set_border(width=stroke["width"] / self.zoom_level)
            annot.update()
            
        if save_to_disk:
            if self.is_new_file:
                # Create notes folder if it doesn't exist
                notes_dir = os.path.join(os.getcwd(), "notes")
                os.makedirs(notes_dir, exist_ok=True)
                
                # Filename is the timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                file_path = os.path.join(notes_dir, f"{timestamp}.pdf")
                
                self.doc.save(file_path)
                self.doc = fitz.open(file_path) # Re-open as real file
                self.is_new_file = False
            else:
                try:
                    self.doc.saveIncr()
                except Exception as e:
                    print(f"Error saving document: {e}")
                    self.doc.save(self.doc.name)
