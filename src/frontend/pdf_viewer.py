import fitz  # PyMuPDF
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPinchGesture, QSwipeGesture, QScroller, QScrollerProperties, QApplication
from PyQt6.QtGui import QPixmap, QImage, QInputDevice, QPointingDevice, QColor, QMouseEvent
from PyQt6.QtCore import Qt, QEvent, QTime
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

        # Double Tap Detection
        self._last_click_time = 0
        self._last_click_pos = None

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
    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Ignore Stylus input (let it pass to Scene for drawing)
        if event.device().type() == QInputDevice.DeviceType.Stylus:
            super().mousePressEvent(event)
            return

        # Double Tap Detection Logic
        current_time = QTime.currentTime().msecsSinceStartOfDay()
        is_double_tap = False
        
        current_pos = event.position().toPoint()

        if self._last_click_pos is not None:
            time_diff = current_time - self._last_click_time
            # Calculate manhattan length manually or use QPoint method
            diff = current_pos - self._last_click_pos
            dist = diff.manhattanLength()
            
            # Thresholds: 400ms and 20 pixels
            if time_diff < 500 and dist < 100:
                is_double_tap = True
        
        self._last_click_time = current_time
        self._last_click_pos = current_pos

        if is_double_tap:
            # Attempt paste
            if self.paste_image_from_clipboard(event.pos()):
                event.accept()
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

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self.paste_image_from_clipboard(event.pos()):
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def paste_image_from_clipboard(self, view_pos) -> bool:
        # Check for clipboard image
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                # Convert to QPixmap
                pixmap = QPixmap.fromImage(image)
                
                # Get position in scene coordinates
                scene_pos = self.mapToScene(view_pos)
                
                # Add to scene
                # Center the image on the cursor/touch point
                item = self.scene.addPixmap(pixmap)
                # Offset by half width/height to center
                item.setPos(scene_pos.x() - pixmap.width() / 2, scene_pos.y() - pixmap.height() / 2)
                
                print(f"[DEBUG] Image pasted from clipboard at {scene_pos}")
                return True
        return False

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
        # Swipe logic needs to be handled by Navigation Module now, or via signals?
        # For now, we'll emit a signal or just leave it broken until we hook it up.
        # Ideally, PDFViewer shouldn't know about "next page" logic if it's modular.
        # But gestures are low-level events.
        # Let's emit a custom signal if we want to be pure, or just access the main window?
        # Accessing main window from here is messy.
        # Let's leave swipe empty for now or assume the Navigation Module will hook into it?
        # Actually, we can just expose a signal `swipe_left` / `swipe_right`.
        pass

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
