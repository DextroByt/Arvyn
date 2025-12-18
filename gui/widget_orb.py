import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, pyqtProperty, pyqtSignal, QRect
from PyQt6.QtGui import QColor

from config import GLASS_STYLE, ORB_SIZE, logger

class ArvynOrb(QWidget):
    """
    The visual heart of the Agent. 
    A floating, glass-morphic orb that pulses and reacts to AI state changes.
    """
    # Custom signal to notify main.py to show/hide the dashboard
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Orb")
        self._setup_ui()
        self._setup_animations()
        
        # For window dragging logic (since it's frameless)
        self.drag_pos = QPoint()

    def _setup_ui(self):
        """Initializes the frameless, translucent window."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(*ORB_SIZE)
        self.setStyleSheet(GLASS_STYLE)

        layout = QVBoxLayout(self)
        self.label = QLabel("A", self) 
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 36px; font-weight: bold; color: white; background: transparent;")
        layout.addWidget(self.label)

    def _setup_animations(self):
        """Creates the breathing/pulsing effect for 'Thinking' mode."""
        self.pulse_anim = QPropertyAnimation(self, b"geometry")
        self.pulse_anim.setDuration(1000)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_anim.setLoopCount(-1)

    def set_state(self, state: str):
        """
        Updates the Orb visuals based on the Agent's state.
        Triggered via BridgeSignals in threads.py.
        """
        logger.debug(f"Orb State Update: {state}")
        
        # Base colors for the gradient
        thinking_color = "rgba(0, 255, 200, 200)"
        success_color = "rgba(46, 204, 113, 220)"
        error_color = "rgba(231, 76, 60, 220)"
        idle_color = "rgba(0, 120, 212, 255)"

        if state == "thinking":
            self.label.setText("...")
            self._start_pulse()
            self._update_style(thinking_color)
        elif state == "success":
            self.pulse_anim.stop()
            self.label.setText("✓")
            self._update_style(success_color)
        elif state == "error":
            self.pulse_anim.stop()
            self.label.setText("!")
            self._update_style(error_color)
        else: # Idle
            self.pulse_anim.stop()
            self.label.setText("A")
            self._update_style(idle_color)

    def _update_style(self, accent_rgba: str):
        """Dynamically re-injects the style with new state colors."""
        new_style = GLASS_STYLE.replace("rgba(0, 120, 212, 255)", accent_rgba)
        self.setStyleSheet(new_style)

    def _start_pulse(self):
        """Calculates and starts the expansion animation."""
        if self.pulse_anim.state() == QPropertyAnimation.State.Running:
            return
            
        geom = self.geometry()
        self.pulse_anim.setStartValue(geom)
        # Pulse expands by 8 pixels
        self.pulse_anim.setEndValue(QRect(geom.x()-4, geom.y()-4, geom.width()+8, geom.height()+8))
        self.pulse_anim.start()

    # --- Interaction Logic ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        """Double click the Orb to toggle the Dashboard."""
        logger.info("Orb double-clicked. Toggling Dashboard...")
        self.clicked.emit()