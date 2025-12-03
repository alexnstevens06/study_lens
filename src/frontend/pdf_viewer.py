import fitz  # PyMuPDF
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPinchGesture, QSwipeGesture
from PyQt6.QtGui import QPixmap, QImage, QInputDevice, QPointingDevice
from PyQt6.QtCore import Qt, QEvent
from src.frontend.ink_canvas import InkCanvas

class PDFViewer(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = InkCanvas(self)
        self.setScene(self.scene)
        self.doc = None
        self.current_page_num = 0
        
        # Optimization: Render at a reasonable scale
        self.zoom_level = 2.0  # 2.0 = 144 DPI (High Quality)
        
        # Enable Gestures
        self.grabGesture(Qt.GestureType.PinchGesture)
        self.grabGesture(Qt.GestureType.SwipeGesture)
        
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
            self.render_page()
        except Exception as e:
            print(f"Error loading document: {e}")

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
        
        # Determine Tool
        if pointer_type == QPointingDevice.PointerType.Eraser:
            self.scene.tool = "eraser"
            # print("Pointer Type: Eraser")
        elif (buttons & Qt.MouseButton.RightButton):
            self.scene.tool = "lasso"
            # print("Right Button Pressed (Lasso)")
        else:
            self.scene.tool = "pencil"

        # Dispatch to Scene
        if event.type() == QEvent.Type.TabletPress:
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
            if self.scene.is_drawing:
                self.scene.end_stroke(pos, pressure)
                self.scene.is_drawing = False
            event.accept()
            return True
            
        return False

    # Manual Panning for Touch/Mouse (ignores Pen which sends TabletEvents)
    def mousePressEvent(self, event: QEvent) -> None:
        print(f"DEBUG: View MousePress Button: {event.button()} Buttons: {event.buttons()} Device: {event.device().type()} Name: {event.device().name()}")
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
        print(f"[DEBUG] gesture_event: {event}")
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
        print(gesture.state())
        if gesture.state() == Qt.GestureState.GestureFinished:
            if gesture.horizontalDirection() == QSwipeGesture.SwipeDirection.Left:
                self.next_page()
            elif gesture.horizontalDirection() == QSwipeGesture.SwipeDirection.Right:
                self.prev_page()

    def next_page(self) -> None:
        if self.doc and self.current_page_num < len(self.doc) - 1:
            self.current_page_num += 1
            self.render_page()

    def prev_page(self) -> None:
        if self.doc and self.current_page_num > 0:
            self.current_page_num -= 1
            self.render_page()
