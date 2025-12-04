import fitz  # PyMuPDF
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPinchGesture, QSwipeGesture, QScroller, QScrollerProperties
from PyQt6.QtGui import QPixmap, QImage, QInputDevice, QPointingDevice, QColor
from PyQt6.QtCore import Qt, QEvent
from src.frontend.ink_canvas import InkCanvas
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
        
        # Enable Gestures
        self.grabGesture(Qt.GestureType.PinchGesture)
        self.grabGesture(Qt.GestureType.SwipeGesture)
        
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
        
        # Panning State
        self._is_panning = False
        self._last_pan_pos = None

    def load_document(self, file_path: str) -> None:
        try:
            self.doc = fitz.open(file_path)
            self.current_page_num = 0
            self.is_new_file = False
            self.render_page()
        except Exception as e:
            print(f"Error loading document: {e}")

    def create_blank_document(self) -> None:
        self.doc = fitz.open()
        # A4 size: 595 x 842 points
        self.doc.new_page(width=595, height=842)
        self.current_page_num = 0
        self.is_new_file = True
        self.render_page()

    def render_page(self) -> None:
        if not self.doc:
            return

        page = self.doc.load_page(self.current_page_num)
        
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
            return self.gesture_event(event)
        return super().event(event)

    def viewportEvent(self, event: QEvent) -> bool:
        if event.type() in [QEvent.Type.TabletPress, QEvent.Type.TabletMove, QEvent.Type.TabletRelease]:
            # Handle Tablet Events
            return self.handle_tablet_event(event)
        return super().viewportEvent(event)

    def handle_tablet_event(self, event: QEvent) -> bool:
        pos = self.mapToScene(event.position().toPoint())
        pressure = event.pressure()
        pointer_type = event.pointerType()
        buttons = event.buttons()
        
        # Determine Tool (Only update if not currently drawing to prevent switching mid-stroke)
        # This ensures that on TabletRelease (when buttons are released), we don't revert to pencil
        if not self.scene.is_drawing:
            if pointer_type == QPointingDevice.PointerType.Eraser:
                self.scene.tool = "eraser"
                # print("Pointer Type: Eraser")

            else:
                self.scene.tool = "pencil"

        # Dispatch to Scene
        if event.type() == QEvent.Type.TabletPress:
            print("[DEBUG] TabletPress received")
            self.scene.is_drawing = True
            self.scene.start_stroke(pos, pressure)
            event.accept()
            return True
            
        elif event.type() == QEvent.Type.TabletMove:
            if self.scene.is_drawing:
                self.scene.move_stroke(pos, pressure)
                event.accept()
                return True
                
        elif event.type() == QEvent.Type.TabletRelease:
            print("[DEBUG] TabletRelease received")
            if self.scene.is_drawing:
                self.scene.end_stroke(pos, pressure)
                self.scene.is_drawing = False
            event.accept()
            return True
            
        return False

    # Manual Panning for Touch/Mouse (ignores Pen which sends TabletEvents)
    def mousePressEvent(self, event: QEvent) -> None:
        # Ignore Stylus input (let it pass to Scene for drawing)
        if event.device().type() == QInputDevice.DeviceType.Stylus:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = True
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QEvent) -> None:
        # Ignore Stylus
        if event.device().type() == QInputDevice.DeviceType.Stylus:
            super().mouseMoveEvent(event)
            return

        if self._is_panning and self._last_pan_pos:
            delta = event.pos() - self._last_pan_pos
            self._last_pan_pos = event.pos()
            
            # Scroll the view
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QEvent) -> None:
        # Ignore Stylus
        if event.device().type() == QInputDevice.DeviceType.Stylus:
            super().mouseReleaseEvent(event)
            return

        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def gesture_event(self, event: QEvent) -> bool:
        pinch = event.gesture(Qt.GestureType.PinchGesture)
        swipe = event.gesture(Qt.GestureType.SwipeGesture)
        
        if pinch:
            self.pinch_triggered(pinch)
        
        if swipe:
            self.swipe_triggered(swipe)
            
        return True

    def pinch_triggered(self, gesture: QPinchGesture) -> None:
        change_flags = gesture.changeFlags()
        if change_flags & QPinchGesture.ChangeFlag.ScaleFactorChanged:
            scale_factor = gesture.scaleFactor()
            self.scale(scale_factor, scale_factor)

    def swipe_triggered(self, gesture: QSwipeGesture) -> None:
        if gesture.state() == Qt.GestureState.GestureFinished:
            if gesture.horizontalDirection() == QSwipeGesture.SwipeDirection.Left:
                self.next_page()
            elif gesture.horizontalDirection() == QSwipeGesture.SwipeDirection.Right:
                self.prev_page()

    def next_page(self) -> None:
        if not self.doc: return
        
        # Save current page annotations before moving
        self.save_annotations(save_to_disk=False)
        
        if self.current_page_num < len(self.doc) - 1:
            self.current_page_num += 1
            self.render_page()
        else:
            # Infinite Scroll: Add new page
            self.doc.new_page(width=595, height=842)
            self.current_page_num += 1
            self.render_page()

    def prev_page(self) -> None:
        if self.doc and self.current_page_num > 0:
            # Save current page annotations before moving
            self.save_annotations(save_to_disk=False)
            self.current_page_num -= 1
            self.render_page()

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
            
        # Clear strokes from scene now that they are in the PDF (so we don't double save if we call this again)
        # Wait, if we clear them, the user sees them disappear until we re-render?
        # Yes, so we should probably re-render or keep them but mark them as saved.
        # For simplicity: We will just NOT clear them, but we risk double saving if save is called multiple times on same page without reload.
        # However, we only call save on page change or close. 
        # If we change page, we re-render anyway.
        
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

    def close_document(self) -> None:
        if self.doc:
            self.save_annotations(save_to_disk=True)
            self.doc.close()
            self.doc = None
            self.scene.clear()
            self.current_page_num = 0
