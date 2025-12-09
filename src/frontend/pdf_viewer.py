import fitz  # PyMuPDF
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPinchGesture, QSwipeGesture, QScroller, QScrollerProperties
from PyQt6.QtGui import QPixmap, QImage, QInputDevice, QPointingDevice, QColor
from PyQt6.QtCore import Qt, QEvent, pyqtSignal
from src.frontend.gestures.base_gesture import BaseGesture
from src.frontend.config_manager import ConfigManager
from src.frontend.loader_utils import load_classes_from_path
from src.frontend.ink_canvas import InkCanvas
from src.frontend.gestures.gesture_manager import GestureManager
from src.frontend.undo_manager import UndoManager, AddStrokeCommand, RemoveStrokeCommand, AddImageCommand, MoveItemsCommand
from PyQt6.QtGui import QKeySequence, QShortcut
import os
from datetime import datetime

class PDFViewer(QGraphicsView):
    document_changed = pyqtSignal()
    page_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.scene = InkCanvas(self)
        self.setScene(self.scene)
        self.doc = None
        self.current_page_num = 0
        self.is_new_file = False
        self.page_data_cache = {} # Cache for strokes and images: {page_num: {"strokes": [], "images": []}}
        
        # Optimization: Render at a reasonable scale
        self.zoom_level = 2.0  # 2.0 = 144 DPI (High Quality)
        
        # Enable Gestures via Manager
        self.gesture_manager = GestureManager(self)
        
        # Undo Manager
        self.undo_manager = UndoManager(self)
        self.connect_undo_signals()
        
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
        self.page_data_cache = {} # Reset cache on new document
        self.render_page()
        self.render_page()
        self.document_changed.emit()

    def connect_undo_signals(self):
        self.scene.strokeCreated.connect(self.on_stroke_created)
        self.scene.strokeErased.connect(self.on_stroke_erased)
        self.scene.itemsMoved.connect(self.on_items_moved)
        self.scene.imageAdded.connect(self.on_image_added)

    def on_stroke_created(self, data):
        cmd = AddStrokeCommand(self.scene, data)
        self.undo_manager.push(cmd)

    def on_stroke_erased(self, data):
        cmd = RemoveStrokeCommand(self.scene, data)
        self.undo_manager.push(cmd)

    def on_items_moved(self, data):
        cmd = MoveItemsCommand(self.scene, data)
        self.undo_manager.push(cmd)

    def on_image_added(self, data):
        cmd = AddImageCommand(self.scene, data)
        self.undo_manager.push(cmd)
    
    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                 self.undo_manager.undo()
                 return
            elif event.key() == Qt.Key.Key_Y:
                 self.undo_manager.redo()
                 return
        super().keyPressEvent(event)

    def get_document(self):
        return self.doc

    def set_page(self, page_num: int) -> None:
        # Save current page data to cache
        if self.doc:
            strokes = self.scene.get_strokes()
            images = self.scene.get_images()
            print(f"[DEBUG] Saving cache for page {self.current_page_num}: {len(strokes)} strokes, {len(images)} images")
            self.page_data_cache[self.current_page_num] = {
                "strokes": strokes,
                "images": images
            }
            
        self.current_page_num = page_num
        self.current_page_num = page_num
        self.render_page()
        self.undo_manager.clear() # Clear undo history on page change
        self.page_changed.emit(page_num)

    def get_page(self) -> int:
        return self.current_page_num

    def refresh_view(self) -> None:
        self.render_page()

    def add_new_page(self) -> None:
        if not self.doc:
            return
            
        # Save current page data to cache
        strokes = self.scene.get_strokes()
        images = self.scene.get_images()
        print(f"[DEBUG] Saving cache for page {self.current_page_num} (before new page): {len(strokes)} strokes, {len(images)} images")
        self.page_data_cache[self.current_page_num] = {
            "strokes": strokes,
            "images": images
        }
            
        # Get dimensions of the last page to match
        width, height = 595, 842 # Default A4
        if self.doc.page_count > 0:
            last_page = self.doc.load_page(self.doc.page_count - 1)
            rect = last_page.rect
            width, height = rect.width, rect.height
            
        self.doc.new_page(width=width, height=height)
        self.current_page_num = self.doc.page_count - 1
        self.render_page()
        self.page_changed.emit(self.current_page_num)
        self.document_changed.emit() # Page count changed, so doc changed too

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
        bg_item = self.scene.addPixmap(pixmap)
        bg_item.setData(Qt.ItemDataRole.UserRole, "background")
        self.setSceneRect(0, 0, pix.width, pix.height)
        
        # Restore strokes and images from cache if available
        if self.current_page_num in self.page_data_cache:
            data = self.page_data_cache[self.current_page_num]
            strokes = data.get("strokes", [])
            images = data.get("images", [])
            print(f"[DEBUG] Restoring cache for page {self.current_page_num}: {len(strokes)} strokes, {len(images)} images")
            self.scene.load_strokes(strokes)
            self.scene.load_images(images)
        else:
            print(f"[DEBUG] No cache found for page {self.current_page_num}")

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
        
        # Save current page to cache first
        self.page_data_cache[self.current_page_num] = {
            "strokes": self.scene.get_strokes(),
            "images": self.scene.get_images()
        }
        
        # Iterate through all cached pages
        for page_num, data in self.page_data_cache.items():
            try:
                page = self.doc.load_page(page_num)
            except Exception as e:
                print(f"[ERROR] Failed to load page {page_num} for saving: {e}")
                continue
                
            strokes = data.get("strokes", [])
            images = data.get("images", [])
            
            # Process Strokes
            page_saved_stroke_ids = []
            for stroke in strokes:
                if stroke.get("saved", False):
                    continue
                    
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
                
                # Add to saved list
                if "id" in stroke:
                    page_saved_stroke_ids.append(stroke["id"])
                    stroke["saved"] = True # Update local cache immediately
            
            # Process Images
            page_saved_image_ids = []
            print(f"[DEBUG] Found {len(images)} images on page {page_num}.")
            for img_data in images:
                if img_data.get("saved", False):
                    continue
                    
                try:
                    # Convert QImage to bytes (PNG format)
                    qimage = img_data["image"]
                    from PyQt6.QtCore import QBuffer, QIODevice
                    ba = QBuffer()
                    ba.open(QIODevice.OpenModeFlag.ReadWrite)
                    qimage.save(ba, "PNG")
                    image_bytes = ba.data().data()
                    
                    # Calculate PDF coordinates
                    # Scene coordinates are zoomed, so divide by zoom_level
                    x = img_data["x"] / self.zoom_level
                    y = img_data["y"] / self.zoom_level
                    w = img_data["width"] / self.zoom_level
                    h = img_data["height"] / self.zoom_level
                    
                    print(f"[DEBUG] Saving image at PDF coords: {x}, {y}, {w}, {h}")
                    
                    # Create rectangle
                    rect = fitz.Rect(x, y, x + w, y + h)
                    
                    # Insert image
                    page.insert_image(rect, stream=image_bytes)
                    print("[DEBUG] Image inserted successfully.")
                    
                    if "id" in img_data:
                        page_saved_image_ids.append(img_data["id"])
                        img_data["saved"] = True # Update local cache immediately
                        
                except Exception as e:
                    print(f"[ERROR] Error saving image: {e}")
            
        if save_to_disk:
            print("[DEBUG] Saving document to disk...")
            
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
                print(f"[DEBUG] Saved new file to {file_path}")
            else:
                # SAFE FULL SAVE STRATEGY
                # Always perform a full save to a temporary file and replace the original.
                # This prevents "xref" errors and "repaired file" issues.
                try:
                    import shutil
                    import time
                    
                    original_path = self.doc.name
                    temp_path = original_path + ".tmp"
                    
                    # Full save with garbage collection and deflation
                    # garbage=4: Remove unused objects
                    # deflate=True: Compress streams
                    self.doc.save(temp_path, garbage=4, deflate=True)
                    self.doc.close()
                    
                    # Robust File Replacement with Retries
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            if os.path.exists(original_path):
                                os.replace(temp_path, original_path)
                            else:
                                os.rename(temp_path, original_path)
                            break # Success
                        except OSError as e_os:
                            if attempt < max_retries - 1:
                                print(f"[WARNING] File replace failed (attempt {attempt+1}/{max_retries}): {e_os}. Retrying...")
                                time.sleep(0.5)
                            else:
                                raise e_os

                    print(f"[DEBUG] Safe full save completed to {original_path}")
                    
                    # Re-open the document
                    self.doc = fitz.open(original_path)
                    
                except Exception as e:
                    print(f"[FATAL] Save failed: {e}")
                    # Attempt recovery
                    if os.path.exists(self.doc.name):
                         self.doc = fitz.open(self.doc.name)

            # Update scene items to show they are saved
            if self.current_page_num in self.page_data_cache:
                current_cache = self.page_data_cache[self.current_page_num]
                saved_stroke_ids = [s["id"] for s in current_cache["strokes"] if s.get("saved")]
                saved_image_ids = [i["id"] for i in current_cache["images"] if i.get("saved")]
                
                self.scene.mark_strokes_as_saved(saved_stroke_ids)
                self.scene.mark_images_as_saved(saved_image_ids)
