import base64
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTextEdit, QStackedWidget, QFrame, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QImage, QColor

from config import DASHBOARD_SIZE, ACCENT_COLOR, ERROR_COLOR, SUCCESS_COLOR

class ArvynDashboard(QFrame):
    """
    Superior Command Center for Agent Arvyn.
    UPGRADED: Autonomous Monitoring Hub (HITL Gates Removed).
    MAINTAINED: High-Resolution Visual Monitor and Semantic Log Streaming.
    """
    command_submitted = pyqtSignal(str)
    mic_clicked = pyqtSignal(bool)
    # approval_given signal kept for backend compatibility, but buttons removed.
    approval_given = pyqtSignal(bool) 
    minimize_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Dashboard")
        self.setFixedSize(DASHBOARD_SIZE[0], DASHBOARD_SIZE[1]) 
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.is_listening = False
        
        self._init_styles()
        self._init_ui()

    def _init_styles(self):
        """Advanced Autonomous Glass Morphism Stylesheet."""
        self.setStyleSheet(f"""
            #Dashboard {{
                background-color: rgba(10, 10, 15, 250);
                border: 1px solid rgba(0, 210, 255, 50);
                border-radius: 24px;
            }}
            QLabel {{ color: #ffffff; font-family: 'Segoe UI', sans-serif; }}
            
            QTextEdit {{
                background: rgba(0, 0, 0, 180);
                color: #d1d1d1;
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 12px;
                font-family: 'Consolas', 'Courier New';
                font-size: 10px;
                line-height: 1.5;
                padding: 10px;
            }}
            
            QLineEdit {{
                background: rgba(255, 255, 255, 8);
                color: #ffffff;
                border: 1px solid rgba(0, 210, 255, 30);
                border-radius: 20px;
                padding: 12px 16px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT_COLOR}; background: rgba(0, 210, 255, 12); }}

            QPushButton {{
                background: rgba(0, 210, 255, 20);
                color: {ACCENT_COLOR};
                border: 1px solid rgba(0, 210, 255, 40);
                border-radius: 10px;
                font-weight: bold;
                font-size: 10px;
                text-transform: uppercase;
            }}
            QPushButton:hover {{ background: rgba(0, 210, 255, 45); color: white; }}
            
            #BtnControl {{ background: transparent; border: none; font-size: 18px; color: #666; }}
            #BtnControl:hover {{ color: {ACCENT_COLOR}; }}
            #BtnStop:hover {{ color: {ERROR_COLOR}; }}
            
            #VisualMonitor {{
                background: #000;
                border: 2px solid rgba(0, 210, 255, 20);
                border-radius: 12px;
            }}

            #AutonomousStatus {{
                background: rgba(0, 210, 255, 10);
                border-radius: 8px;
                padding: 5px;
            }}
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)

        # --- 1. Header Area ---
        header_layout = QHBoxLayout()
        self.header = QLabel("ARVYN // AUTONOMOUS HUB")
        self.header.setStyleSheet(f"font-weight: 900; letter-spacing: 2px; font-size: 10px; color: {ACCENT_COLOR};")
        
        btn_min = QPushButton("−")
        btn_min.setObjectName("BtnControl")
        btn_min.setFixedSize(28, 28)
        btn_min.clicked.connect(self.minimize_requested.emit)

        btn_stop = QPushButton("×")
        btn_stop.setObjectName("BtnControl")
        btn_stop.setObjectName("BtnStop")
        btn_stop.setFixedSize(28, 28)
        btn_stop.clicked.connect(self.stop_requested.emit)
        
        header_layout.addWidget(self.header)
        header_layout.addStretch()
        header_layout.addWidget(btn_min)
        header_layout.addWidget(btn_stop)
        layout.addLayout(header_layout)

        # --- 2. Live Visual Monitor ---
        self.visual_monitor = QLabel()
        self.visual_monitor.setObjectName("VisualMonitor")
        self.visual_monitor.setFixedSize(310, 195)
        self.visual_monitor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.visual_monitor.setText("SECURE OPTIC FEED: OFFLINE")
        self.visual_monitor.setStyleSheet("color: #333; font-size: 9px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(self.visual_monitor)

        # --- 3. Autonomous Activity Monitor (Replaced HITL Buttons) ---
        self.status_hub = QFrame()
        self.status_hub.setObjectName("AutonomousStatus")
        self.status_hub.setFixedHeight(60)
        hub_lay = QVBoxLayout(self.status_hub)
        hub_lay.setContentsMargins(10, 8, 10, 8)
        hub_lay.setSpacing(2)

        self.status_msg = QLabel("SYSTEM IDLE")
        self.status_msg.setStyleSheet(f"color: {ACCENT_COLOR}; font-weight: 900; font-size: 11px; letter-spacing: 1.5px;")
        self.status_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.kinetic_status = QLabel("MONITORING NETWORK")
        self.kinetic_status.setStyleSheet("color: #666; font-weight: 700; font-size: 8px; text-transform: uppercase;")
        self.kinetic_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hub_lay.addWidget(self.status_msg)
        hub_lay.addWidget(self.kinetic_status)
        layout.addWidget(self.status_hub)

        # --- 4. Logic & Interaction Stack (Now for alerts only) ---
        self.interaction_stack = QStackedWidget()
        self.interaction_stack.setFixedHeight(25)
        
        self.empty_spacer = QWidget()
        self.alert_msg = QLabel("SECURE DATA INJECTION ACTIVE")
        self.alert_msg.setStyleSheet(f"color: {SUCCESS_COLOR}; font-size: 9px; font-weight: bold;")
        self.alert_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.interaction_stack.addWidget(self.empty_spacer)
        self.interaction_stack.addWidget(self.alert_msg)
        layout.addWidget(self.interaction_stack)

        # --- 5. Semantic Log Area ---
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Streaming autonomous reasoning...")
        layout.addWidget(self.log_area)

        # --- 6. Unified Command Input ---
        cmd_layout = QHBoxLayout()
        cmd_layout.setSpacing(10)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter goal...")
        self.input_field.returnPressed.connect(self._handle_submit)
        
        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setFixedSize(44, 44)
        self.btn_mic.setStyleSheet("background-color: #ff3b30; border-radius: 22px; border: none; font-size: 18px;")
        self.btn_mic.clicked.connect(self._toggle_mic)

        cmd_layout.addWidget(self.input_field)
        cmd_layout.addWidget(self.btn_mic)
        layout.addLayout(cmd_layout)

    def _toggle_mic(self):
        """Manages mic state with visual feedback."""
        if not self.is_listening:
            self.is_listening = True
            self.btn_mic.setStyleSheet("background-color: #4cd964; border-radius: 22px; border: none; font-size: 18px;")
            self.append_log("[VOICE] MIC ACTIVE: LISTENING FOR GOAL", category="system")
        else:
            self.is_listening = False
            self.btn_mic.setStyleSheet("background-color: #ff3b30; border-radius: 22px; border: none; font-size: 18px;")
            self.append_log("[VOICE] MIC CLOSED: PARSING COMMAND", category="system")
        self.mic_clicked.emit(self.is_listening)

    def _handle_submit(self):
        """Processes text input goals."""
        text = self.input_field.text().strip()
        if text:
            self.command_submitted.emit(text)
            self.input_field.clear()

    def append_log(self, text: str, category: str = "general"):
        """Categorical log processing with semantic color mapping."""
        colors = {
            "action": ACCENT_COLOR,
            "system": "#777777",
            "error": ERROR_COLOR,
            "success": SUCCESS_COLOR,
            "kinetic": "#f1c40f",
            "secure": "#9b59b6", # Purple for PIN/Password actions
            "general": "#cccccc"
        }
        
        text_lower = text.lower()
        # Semantic Auto-Detection
        if any(k in text_lower for k in ["[action]", "[brain]", "reasoning"]): category = "action"
        elif any(k in text_lower for k in ["[error]", "failed", "fault"]): category = "error"
        elif any(k in text_lower for k in ["completed", "success", "🏁"]): category = "success"
        elif any(k in text_lower for k in ["kinetic", "interaction"]): category = "kinetic"
        elif any(k in text_lower for k in ["injecting", "secure", "pin", "credential"]): category = "secure"
        elif any(k in text_lower for k in ["[intent", "[discovery"]): category = "system"

        color = colors.get(category, colors["general"])
        formatted_text = f"<div style='margin-bottom: 5px;'><span style='color:{color}; font-weight:900;'>&gt;</span> {text}</div>"
        
        self.log_area.append(formatted_text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        
        # Sync the Hub Status with the latest significant log
        if category in ["action", "kinetic", "secure"]:
            clean_text = text.split("]")[-1].strip() if "]" in text else text
            self.kinetic_status.setText(clean_text[:40].upper())

    def update_screenshot(self, b64_data: str):
        """Renders the browser view into the Dashboard optic monitor."""
        try:
            img_data = base64.b64decode(b64_data)
            image = QImage.fromData(img_data)
            pixmap = QPixmap.fromImage(image)
            scaled_pixmap = pixmap.scaled(
                self.visual_monitor.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.visual_monitor.setPixmap(scaled_pixmap)
            self.status_msg.setText("ACTIVE MONITORING")
        except Exception as e:
            self.append_log(f"Optic Feed Error: {e}", category="error")

    def show_secure_alert(self, duration: int = 3000):
        """Briefly highlights the status area when secure data is injected."""
        self.interaction_stack.setCurrentIndex(1)
        self.status_hub.setStyleSheet(f"background: rgba(46, 204, 113, 30); border-radius: 8px; border: 1px solid {SUCCESS_COLOR};")
        
        QTimer.singleShot(duration, self._reset_hub_style)

    def _reset_hub_style(self):
        """Returns the hub to its standard state."""
        self.interaction_stack.setCurrentIndex(0)
        self.status_hub.setStyleSheet("background: rgba(0, 210, 255, 10); border-radius: 8px; padding: 5px;")