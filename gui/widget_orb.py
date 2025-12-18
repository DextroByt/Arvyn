from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen
from qframelesswindow import AcrylicWindow

from config import ORB_SIZE, GLASS_STYLE, ACCENT_COLOR

class ArvynOrb(AcrylicWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._setup_window_properties()
        self._init_ui()
        self._init_animations()
        
        # Internal state for dragging
        self.old_pos = None

    def _setup_window_properties(self):
        """Sets up the floating, frameless, and transparent attributes."""
        # Fix: Using explicit WindowType and WidgetAttribute namespaces
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(ORB_SIZE[0], ORB_SIZE[1])
        
        # Apply the native Windows 11 Acrylic effect
        self.windowEffect.setAcrylicEffect(self.winId(), "1E1E1E99")

    def _init_ui(self):
        """Creates the visual layout of the Orb."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.orb_widget = QWidget(self)
        self.orb_widget.setObjectName("Orb")
        self.orb_widget.setStyleSheet(GLASS_STYLE)
        
        self.layout.addWidget(self.orb_widget)

    def _init_animations(self):
        """Initializes the 'Breathing' pulse effect."""
        self._pulse_alpha = 180
        self.pulse_anim = QPropertyAnimation(self, b"pulse_alpha")
        self.pulse_anim.setDuration(2000)
        self.pulse_anim.setStartValue(100)
        self.pulse_anim.setEndValue(220)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_anim.setLoopCount(-1) 
        self.pulse_anim.start()

    @pyqtProperty(int)
    def pulse_alpha(self):
        return self._pulse_alpha

    @pulse_alpha.setter
    def pulse_alpha(self, value):
        self._pulse_alpha = value
        self.update()

    # ==========================================
    # INTERACTION LOGIC (DRAG & CLICK)
    # ==========================================
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def mouseDoubleClickEvent(self, event):
        """Summons the full Dashboard on double click."""
        if hasattr(self, 'toggle_dashboard'):
            self.toggle_dashboard()

    def paintEvent(self, event):
        """Custom painting for the circular glow and glass effect."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor(ACCENT_COLOR)
        color.setAlpha(self._pulse_alpha)
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.GlobalColor.white, 1, Qt.PenStyle.SolidLine))
        
        painter.drawEllipse(5, 5, self.width()-10, self.height()-10)