from PyQt6.QtGui import QAction, QPainter, QColor, QPen, QBrush, QPixmap, QFont, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton, 
    QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QSize
from .base_module import BaseModule

class RGBSliders(QWidget):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, initial_color: QColor, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self) # Stack horizontal sliders vertically
        
        self.red_slider = self._create_slider(initial_color.red(), "red")
        self.green_slider = self._create_slider(initial_color.green(), "green")
        self.blue_slider = self._create_slider(initial_color.blue(), "blue")

        layout.addWidget(self.red_slider)
        layout.addWidget(self.green_slider)
        layout.addWidget(self.blue_slider)

    def _create_slider(self, value, color_name):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(value)
        slider.valueChanged.connect(self._emit_color_change)
        
        # Style: Groove gradient from Black (left) to Color (right)
        css = f"""
            QSlider::groove:horizontal {{
                border: 1px solid #999;
                height: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 black, stop:1 {color_name});
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: white;
                border: 1px solid #555;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}
            QSlider::add-page:horizontal {{
                background: transparent;
            }}
            QSlider::sub-page:horizontal {{
                background: transparent;
            }}
        """
        slider.setStyleSheet(css)
        return slider

    def _emit_color_change(self):
        r = self.red_slider.value()
        g = self.green_slider.value()
        b = self.blue_slider.value()
        self.colorChanged.emit(QColor(r, g, b))

    def set_color(self, color: QColor):
        self.red_slider.blockSignals(True)
        self.green_slider.blockSignals(True)
        self.blue_slider.blockSignals(True)
        self.red_slider.setValue(color.red())
        self.green_slider.setValue(color.green())
        self.blue_slider.setValue(color.blue())
        self.red_slider.blockSignals(False)
        self.green_slider.blockSignals(False)
        self.blue_slider.blockSignals(False)

class PenPreview(QWidget):
    def __init__(self, color: QColor, size: float, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 80)
        self.current_color = color
        self.current_size = size

    def update_preview(self, color: QColor, size: float):
        self.current_color = color
        self.current_size = size
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        
        # 1. Vertical Color Strips on Left and Right
        strip_width = 20
        # For preview, we show the color including alpha over white
        painter.fillRect(0, 0, strip_width, self.height(), self.current_color)
        painter.fillRect(self.width() - strip_width, 0, strip_width, self.height(), self.current_color)
        
        # 2. Pen Tip in Center
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.current_color))
        painter.drawEllipse(QPointF(center_x, center_y), self.current_size/2, self.current_size/2)

class RecentPens(QWidget):
    penSelected = pyqtSignal(dict) # {color: QColor, size: float}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pens = [] # List of dicts
        self.buttons = []
        self.grid_layout = QHBoxLayout(self)
        self.grid_layout.setSpacing(5)
        
        # Create 6 placeholder buttons
        for i in range(6):
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.clicked.connect(lambda checked, idx=i: self._on_btn_clicked(idx))
            self.grid_layout.addWidget(btn)
            self.buttons.append(btn)

    def add_pen(self, color: QColor, size: float):
        # Add to start, limit to 6
        pen_data = {"color": color, "size": size}
        
        # Remove if exact duplicate exists 
        self.pens = [p for p in self.pens if not (p["color"] == color and p["size"] == size)]
        
        self.pens.insert(0, pen_data)
        if len(self.pens) > 6:
            self.pens = self.pens[:6]
        
        self._update_buttons()

    def _update_buttons(self):
        for i, btn in enumerate(self.buttons):
            if i < len(self.pens):
                pen = self.pens[i]
                self._style_button(btn, pen["color"], pen["size"])
                btn.setEnabled(True)
            else:
                btn.setStyleSheet("background-color: #eee; border: 1px solid #ccc;")
                btn.setIcon(QIcon()) # Clear icon
                btn.setEnabled(False)

    def _style_button(self, btn, color, size):
        # Draw a mini preview icon
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        
        # Scale size to fit (max 24px circle)
        display_size = min(24, max(4, size * 2)) 
        center = 16
        painter.drawEllipse(QPointF(center, center), display_size/2, display_size/2)
        painter.end()
        
        btn.setIcon(QIcon(pixmap))
        btn.setIconSize(QSize(32, 32))
        btn.setStyleSheet("border: 1px solid #999; border-radius: 4px;")

    def _on_btn_clicked(self, idx):
        if idx < len(self.pens):
            self.penSelected.emit(self.pens[idx])

class PenSettingsPopup(QWidget):
    penSettingsChanged = pyqtSignal(QColor, int) # Color, Size

    def __init__(self, initial_color: QColor, initial_size: int, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Pen Settings")
        self.setFixedSize(320, 580)
        
        self.current_color = initial_color
        self.current_size = initial_size
        self.current_alpha = initial_color.alpha()
        
        layout = QVBoxLayout(self)
        
        # 1. RGB Sliders (Top)
        layout.addWidget(QLabel("RGB Channels"))
        self.rgb_sliders = RGBSliders(initial_color)
        self.rgb_sliders.colorChanged.connect(self._on_rgb_changed)
        layout.addWidget(self.rgb_sliders)
        
        # 2. Opacity Slider
        layout.addWidget(QLabel("Opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setValue(self.current_alpha)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        layout.addWidget(self.opacity_slider)

        # 3. Size Slider
        layout.addWidget(QLabel("Size"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(1, 40)
        self.size_slider.setValue(initial_size)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        layout.addWidget(self.size_slider)
        
        # 4. Preview
        layout.addWidget(QLabel("Preview"))
        self.preview = PenPreview(initial_color, initial_size)
        layout.addWidget(self.preview)
        
        # 5. Recent Pens
        layout.addWidget(QLabel("Recent Pens"))
        self.recent_pens = RecentPens()
        self.recent_pens.add_pen(initial_color, initial_size)
        self.recent_pens.penSelected.connect(self._on_recent_selected)
        layout.addWidget(self.recent_pens)
        
        # 6. Save and Close Button
        self.save_btn = QPushButton("Save and Close")
        self.save_btn.clicked.connect(self._on_save_close)
        self.save_btn.setFixedHeight(40)
        font = self.save_btn.font()
        font.setBold(True)
        self.save_btn.setFont(font)
        layout.addWidget(self.save_btn)

    def _on_rgb_changed(self, color):
        # Update color but preserve current alpha
        self.current_color = color
        self.current_color.setAlpha(self.current_alpha)
        self._update_all()

    def _on_opacity_changed(self, value):
        self.current_alpha = value
        self.current_color.setAlpha(self.current_alpha)
        self._update_all()

    def _on_size_changed(self, value):
        self.current_size = value
        self._update_all()

    def _update_all(self):
        self.preview.update_preview(self.current_color, self.current_size)
        # Live update canvas
        self.penSettingsChanged.emit(self.current_color, self.current_size)

    def _on_recent_selected(self, pen_data):
        self.current_color = pen_data["color"]
        self.current_size = pen_data["size"]
        self.current_alpha = self.current_color.alpha()
        
        # Update controls
        self.rgb_sliders.set_color(self.current_color)
        
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(self.current_alpha)
        self.opacity_slider.blockSignals(False)
        
        self.size_slider.blockSignals(True)
        self.size_slider.setValue(int(self.current_size))
        self.size_slider.blockSignals(False)
        
        self._update_all()

    def _on_save_close(self):
        self.recent_pens.add_pen(self.current_color, self.current_size)
        self.hide()

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
            self._create_popup()
            self.pen_settings_popup.show()
        else:
            if self.pen_settings_popup.isVisible():
                self.pen_settings_popup.hide()
            else:
                self.pen_settings_popup.show()

    def _create_popup(self):
        current_color = self.main_window.pdf_viewer.scene.pen_color
        current_size = int(self.main_window.pdf_viewer.scene.pen_width)
        
        self.pen_settings_popup = PenSettingsPopup(current_color, current_size, self.main_window)
        self.pen_settings_popup.penSettingsChanged.connect(self.update_pen_settings)

    def update_pen_settings(self, color, size):
        self.main_window.pdf_viewer.scene.pen_color = color
        self.main_window.pdf_viewer.scene.pen_width = size
