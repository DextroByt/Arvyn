import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from config import logger, ORB_SIZE, ACCENT_COLOR, DASHBOARD_SIZE

class ArvynOrb(QWidget):
    """
    The Visual Base for Agent Arvyn.
    Handles the floating orb UI, animations (pulse), and transparency.
    """
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Setup Frameless, Transparent Window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Initial size from config
        self.resize(ORB_SIZE, ORB_SIZE)

        # Base Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Status Label (The 'Orb' itself)
        self.status_label = QLabel("A")
        self.status_label.setFixedSize(ORB_SIZE - 20, ORB_SIZE - 20)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # UI Styling using the Accent Color from Config
        self.orb_style_base = f"""
            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                stop:0 rgba(0, 210, 255, 180), stop:1 rgba(58, 123, 213, 180));
            color: white;
            border-radius: {(ORB_SIZE - 20) // 2}px;
            font-size: 32px;
            font-weight: bold;
            border: 2px solid white;
        """
        self.status_label.setStyleSheet(self.orb_style_base)
        self.layout.addWidget(self.status_label)
        
        self.expansion_anim = None

    def mousePressEvent(self, event):
        """Triggers the dashboard expansion on left click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def start_pulse(self):
        """Visual feedback: brighten the orb when active."""
        self.status_label.setStyleSheet(self.orb_style_base.replace("180", "255"))

    def stop_pulse(self):
        """Visual feedback: dim the orb when idle."""
        self.status_label.setStyleSheet(self.orb_style_base.replace("255", "180"))