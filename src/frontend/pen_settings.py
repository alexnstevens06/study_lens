from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, 
                             QSlider, QLabel, QPushButton, QFrame)
from PyQt6.QtGui import (QPainter, QColor, QConicalGradient, QRadialGradient, 
                         QBrush, QPen, QMouseEvent)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QSize
import math

class ColorWheel(QWidget):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.hue = 0.0
        self.saturation = 0.0
        self.value = 1.0  # Brightness
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

        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 5

        # 1. Conical Gradient for Hue
        conical = QConicalGradient(center, 90)
        for i in range(360):
            conical.setColorAt(i / 360.0, QColor.fromHsvF(i / 360.0, 1.0, 1.0))
        conical.setColorAt(1.0, QColor.fromHsvF(0.0, 1.0, 1.0))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(conical))
        painter.drawEllipse(center, radius, radius)

        # 2. Radial Gradient for Saturation (White center to Transparent edge)
        # Actually, to mix correctly with Value, we usually do:
        # Hue Wheel (Full Sat/Val) -> Overlay White (Sat) -> Overlay Black (Val)
        # But for a simple Hue/Sat wheel:
        # Center is White (Sat=0), Edge is Pure Color (Sat=1)
        
        radial = QRadialGradient(center, radius)
        radial.setColorAt(0, QColor.fromHsvF(0, 0, 1.0, 1.0)) # White center
        radial.setColorAt(1, QColor.fromHsvF(0, 0, 1.0, 0.0)) # Transparent edge
        
        painter.setBrush(QBrush(radial))
        painter.drawEllipse(center, radius, radius)
        
        # 3. Overlay for Value (Black with alpha)
        # If value < 1.0, we draw a black circle with alpha = 1 - value
        if self.value < 1.0:
            black_overlay = QColor(0, 0, 0)
            black_overlay.setAlphaF(1.0 - self.value)
            painter.setBrush(QBrush(black_overlay))
            painter.drawEllipse(center, radius, radius)

        # 4. Draw Selector
        # Calculate position based on Hue (angle) and Saturation (distance)
        angle_rad = self.hue * 2 * math.pi
        # Adjust for QConicalGradient starting at 90 degrees (North)? 
        # QConicalGradient starts at 3 o'clock (0 degrees) by default? No, docs say 0 is 3 o'clock.
        # But we want Red at 0? 
        # Let's just map click pos to hue/sat directly.
        
        # Re-calculate pos from hue/sat
        # Hue 0 is usually Red. In QConical, 0.0 is 3 o'clock.
        # Angle is negative for standard math (CCW) vs Qt (CW)?
        
        # Simple polar to cartesian
        r = self.saturation * radius
        # QConicalGradient at 0.0 is 3 o'clock.
        # We want to match the visual.
        # Visual: 0.0 is Red.
        
        # Let's just trust the angle logic from mouse event
        angle = self.hue * 360
        # Convert to radians. Note: y is inverted in screen coords?
        # Let's stick to standard math: x = r * cos(a), y = r * sin(a)
        # But we need to offset by 90 degrees if we rotated the gradient?
        # I set QConicalGradient(center, 90). This puts 0.0 at 90 degrees (12 o'clock)?
        # Let's check docs or just try.
        # If startAngle is 90, then 0.0 is at 90 degrees (North).
        # So angle_rad should be relative to North?
        # Actually, let's just use the mouse logic to be consistent.
        
        # Selector position
        # We need to inverse the logic from mousePress
        # But for now, let's just draw it where the mouse clicked (stored in hue/sat)
        
        # Angle in degrees: (hue * 360)
        # But we shifted gradient by 90.
        # So visual angle = 90 - (hue * 360) ?
        
        # Let's implement mouse logic first to define the mapping.
        
        selector_x = center.x() + self.saturation * radius * math.cos(math.radians(90 - self.hue * 360))
        selector_y = center.y() - self.saturation * radius * math.sin(math.radians(90 - self.hue * 360))
        
        painter.setPen(QPen(Qt.GlobalColor.black if self.value > 0.5 else Qt.GlobalColor.white, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(selector_x, selector_y), 5, 5)

    def mousePressEvent(self, event: QMouseEvent):
        self._handle_mouse(event.position())

    def mouseMoveEvent(self, event: QMouseEvent):
        self._handle_mouse(event.position())

    def _handle_mouse(self, pos: QPointF):
        center = QPointF(self.width() / 2, self.height() / 2)
        dx = pos.x() - center.x()
        dy = center.y() - pos.y() # Invert Y so up is positive
        
        dist = math.sqrt(dx*dx + dy*dy)
        radius = min(self.width(), self.height()) / 2 - 5
        
        self.saturation = min(1.0, dist / radius)
        
        # Angle
        angle_deg = math.degrees(math.atan2(dy, dx))
        # atan2 returns -180 to 180.
        # 0 is East (3 o'clock). 90 is North.
        # We want 0..1 to map to 0..360 starting from North (since we rotated gradient to 90)
        # Gradient 0.0 is at 90 deg.
        # So Hue 0.0 should be at 90 deg.
        
        # Map angle_deg to 0..1
        # 90 deg -> 0.0
        # 0 deg -> 0.25
        # -90 deg -> 0.5
        # 180/-180 -> 0.75
        
        # hue = (90 - angle) / 360
        hue = (90 - angle_deg) / 360.0
        if hue < 0:
            hue += 1.0
            
        self.hue = hue
        self._update_color()
        self.update()

class PenSettingsDialog(QDialog):
    penSettingsChanged = pyqtSignal(QColor, int) # Color, Size

    def __init__(self, initial_color: QColor, initial_size: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pen Settings")
        self.setFixedSize(300, 450)
        
        layout = QVBoxLayout(self)
        
        # 1. Color Wheel
        self.color_wheel = ColorWheel()
        # Init from initial_color
        h, s, v, _ = initial_color.getHsvF()
        self.color_wheel.hue = h
        self.color_wheel.saturation = s
        self.color_wheel.value = v
        self.color_wheel.current_color = initial_color
        
        wheel_layout = QHBoxLayout()
        wheel_layout.addStretch()
        wheel_layout.addWidget(self.color_wheel)
        wheel_layout.addStretch()
        layout.addLayout(wheel_layout)
        
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
        # We'll paint the preview manually or just set background? 
        # Better to paint a dot.
        
        # Let's use a custom paint event for preview frame or just a label
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(280, 60)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_label)
        
        # Connect signals
        self.color_wheel.colorChanged.connect(self._on_color_changed)
        
        # Initial update
        self._update_preview()

    def _on_brightness_changed(self, value):
        self.color_wheel.set_value(value / 100.0)

    def _on_color_changed(self, color):
        self._update_preview()

    def _update_preview(self):
        color = self.color_wheel.current_color
        size = self.size_slider.value()
        
        # Create a pixmap for preview
        pixmap = self.preview_label.grab() # Grab existing or create new?
        # Just create new
        from PyQt6.QtGui import QPixmap
        pixmap = QPixmap(280, 60)
        pixmap.fill(Qt.GlobalColor.white)
        
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
