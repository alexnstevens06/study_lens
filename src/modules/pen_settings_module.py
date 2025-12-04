from PyQt6.QtGui import QAction, QPainter, QColor, QLinearGradient, QBrush, QPen, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QSize
from .base_module import BaseModule

class ColorBar(QWidget):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 40)
        self.hue = 0.0
        self.saturation = 1.0
        self.value = 1.0
        self.current_color = QColor.fromHsvF(self.hue, self.saturation, self.value)

    def set_value(self, value: float):
        self.value = max(0.0, min(1.0, value))
        self._update_color()
        self.update()

    def _update_color(self):
        self.current_color = QColor.fromHsvF(self.hue, self.saturation, self.value)
        self.colorChanged.emit(self.current_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Hue Gradient (Background for both halves)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        for i in range(361):
            gradient.setColorAt(i / 360.0, QColor.fromHsvF(i / 360.0, 1.0, 1.0))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self.width(), self.height())

        # Draw Value Overlay (Black with alpha) - ONLY on Bottom Half
        if self.value < 1.0:
            black_overlay = QColor(0, 0, 0)
            black_overlay.setAlphaF(1.0 - self.value)
            painter.setBrush(QBrush(black_overlay))
            # Draw on bottom half
            half_height = int(self.height() / 2)
            painter.drawRect(0, half_height, self.width(), self.height() - half_height)

        # Draw Selector
        selector_x = self.hue * self.width()
        
        # Draw selector line
        pen_color = Qt.GlobalColor.black if self.value > 0.5 else Qt.GlobalColor.white
        painter.setPen(QPen(pen_color, 2))
        painter.drawLine(int(selector_x), 0, int(selector_x), self.height())

    def mousePressEvent(self, event: QMouseEvent):
        self._handle_mouse(event.position().x())

    def mouseMoveEvent(self, event: QMouseEvent):
        self._handle_mouse(event.position().x())

    def _handle_mouse(self, x):
        x = max(0, min(x, self.width()))
        self.hue = x / self.width()
        self._update_color()
        self.update()

class PenSettingsPopup(QWidget):
    penSettingsChanged = pyqtSignal(QColor, int) # Color, Size

    def __init__(self, initial_color: QColor, initial_size: int, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Pen Settings")
        self.setFixedSize(300, 350) 
        
        layout = QVBoxLayout(self)
        
        # 1. Color Bar
        layout.addWidget(QLabel("Color"))
        self.color_bar = ColorBar()
        # Init from initial_color
        h, s, v, _ = initial_color.getHsvF()
        self.color_bar.hue = h
        self.color_bar.saturation = 1.0 
        self.color_bar.value = v
        self.color_bar.current_color = initial_color
        layout.addWidget(self.color_bar)
        
        # 2. Brightness Slider
        layout.addWidget(QLabel("Brightness (Value)"))
        self.bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.bright_slider.setRange(0, 100)
        self.bright_slider.setValue(int(v * 100))
        self.bright_slider.valueChanged.connect(self._on_brightness_changed)
        layout.addWidget(self.bright_slider)
        
        # 3. Size Slider
        layout.addWidget(QLabel("Size"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(1, 50)
        self.size_slider.setValue(initial_size)
        self.size_slider.valueChanged.connect(self._update_preview)
        layout.addWidget(self.size_slider)
        
        # 4. Preview
        layout.addWidget(QLabel("Preview"))
        self.preview_frame = QFrame()
        self.preview_frame.setFixedSize(280, 60)
        self.preview_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.preview_frame.setAutoFillBackground(True)
        
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(280, 60)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_label)
        
        # Connect signals
        self.color_bar.colorChanged.connect(self._on_color_changed)
        
        # Initial update
        self._update_preview()

    def _on_brightness_changed(self, value):
        self.color_bar.set_value(value / 100.0)

    def _on_color_changed(self, color):
        self._update_preview()

    def _update_preview(self):
        color = self.color_bar.current_color
        size = self.size_slider.value()
        
        # Set white for background
        bg_color = QColor(255, 255, 255)
        
        # Create a pixmap for preview
        pixmap = QPixmap(280, 60)
        pixmap.fill(bg_color)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        
        center = QPointF(140, 30)
        painter.drawEllipse(center, size/2, size/2)
        painter.end()
        
        self.preview_label.setPixmap(pixmap)
        
        # Emit signal
        self.penSettingsChanged.emit(color, size)

class PenSettingsModule(BaseModule):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.pen_settings_popup = None

    @property
    def priority(self):
        return 40

    def get_actions(self):
        pen_settings_action = QAction("Pen Settings", self.main_window)
        pen_settings_action.triggered.connect(self.toggle_pen_settings)
        return [pen_settings_action]

    def toggle_pen_settings(self):
        if not self.pen_settings_popup:
            # Get current settings from scene
            current_color = self.main_window.pdf_viewer.scene.pen_color
            current_size = int(self.main_window.pdf_viewer.scene.pen_width)
            
            self.pen_settings_popup = PenSettingsPopup(current_color, current_size, self.main_window)
            self.pen_settings_popup.penSettingsChanged.connect(self.update_pen_settings)
            self.pen_settings_popup.show()
        else:
            if self.pen_settings_popup.isVisible():
                self.pen_settings_popup.hide()
            else:
                self.pen_settings_popup.show()

    def update_pen_settings(self, color, size):
        self.main_window.pdf_viewer.scene.pen_color = color
        self.main_window.pdf_viewer.scene.pen_width = size
