import base64
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTextEdit, QStackedWidget, QFrame, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QImage, QColor

from config import DASHBOARD_SIZE, ACCENT_COLOR, ERROR_COLOR, SUCCESS_COLOR

class ArvynDashboard(QFrame):
    """
    Superior Command Center for Agent Arvyn.
    UPGRADED: High-Resolution Visual Monitor, Semantic Log Streaming, 
    and Advanced Glass Morphism UI optimized for 1080p browsing.
    """
    command_submitted = pyqtSignal(str)
    mic_clicked = pyqtSignal(bool)
    approval_given = pyqtSignal(bool)
    minimize_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Dashboard")
        # Expanded size to 500x750 as per production requirements
        self.setFixedSize(DASHBOARD_SIZE[0], DASHBOARD_SIZE[1]) 
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.is_listening = False
        
        self._init_styles()
        self._init_ui()

    def _init_styles(self):
        """Advanced Glass Morphism Stylesheet with semantic highlighting."""
        self.setStyleSheet(f"""
            #Dashboard {{
                background-color: rgba(15, 15, 20, 245);
                border: 1px solid rgba(0, 210, 255, 30);
                border-radius: 28px;
            }}
            QLabel {{ color: #ffffff; font-family: 'Segoe UI', sans-serif; }}
            
            QTextEdit {{
                background: rgba(0, 0, 0, 140);
                color: #d1d1d1;
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 14px;
                font-family: 'Consolas', 'Courier New';
                font-size: 11px;
                line-height: 1.5;
                padding: 10px;
            }}
            
            QLineEdit {{
                background: rgba(255, 255, 255, 8);
                color: #ffffff;
                border: 1px solid rgba(0, 210, 255, 40);
                border-radius: 20px;
                padding: 12px 18px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT_COLOR}; background: rgba(0, 210, 255, 12); }}

            QPushButton {{
                background: rgba(0, 210, 255, 25);
                color: {ACCENT_COLOR};
                border: 1px solid rgba(0, 210, 255, 50);
                border-radius: 12px;
                font-weight: bold;
                font-size: 11px;
                text-transform: uppercase;
            }}
            QPushButton:hover {{ background: rgba(0, 210, 255, 50); color: white; }}
            
            #BtnControl {{ background: transparent; border: none; font-size: 20px; color: #777; }}
            #BtnControl:hover {{ color: {ACCENT_COLOR}; }}
            #BtnStop:hover {{ color: {ERROR_COLOR}; }}
            
            #BtnApprove {{ background: rgba(46, 204, 113, 25); border-color: #2ecc71; color: #2ecc71; }}
            #BtnReject {{ background: rgba(231, 76, 60, 25); border-color: {ERROR_COLOR}; color: {ERROR_COLOR}; }}
            
            #VisualMonitor {{
                background: #000;
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: 12px;
            }}
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 25)
        layout.setSpacing(15)

        # --- 1. Header Area ---
        header_layout = QHBoxLayout()
        self.header = QLabel("ARVYN // COMMAND CENTER")
        self.header.setStyleSheet(f"font-weight: 900; letter-spacing: 2px; font-size: 11px; color: {ACCENT_COLOR};")
        
        btn_min = QPushButton("−")
        btn_min.setObjectName("BtnControl")
        btn_min.setFixedSize(32, 32)
        btn_min.clicked.connect(self.minimize_requested.emit)

        btn_stop = QPushButton("×")
        btn_stop.setObjectName("BtnControl")
        btn_stop.setObjectName("BtnStop")
        btn_stop.setFixedSize(32, 32)
        btn_stop.clicked.connect(self.stop_requested.emit)
        
        header_layout.addWidget(self.header)
        header_layout.addStretch()
        header_layout.addWidget(btn_min)
        header_layout.addWidget(btn_stop)
        layout.addLayout(header_layout)

        # --- 2. Live Visual Monitor ---
        # Expanded to handle high-res 1080p feed visualization
        self.visual_monitor = QLabel()
        self.visual_monitor.setObjectName("VisualMonitor")
        self.visual_monitor.setFixedSize(450, 280)
        self.visual_monitor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.visual_monitor.setText("AWAITING SECURE FEED...")
        self.visual_monitor.setStyleSheet("color: #555; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(self.visual_monitor)

        # --- 3. Interaction Status ---
        self.interaction_stack = QStackedWidget()
        self.interaction_stack.setFixedHeight(55)

        self.status_container = QWidget()
        status_lay = QVBoxLayout(self.status_container)
        status_lay.setContentsMargins(0, 0, 0, 0)
        self.status_msg = QLabel("SYSTEM STANDBY")
        self.status_msg.setStyleSheet(f"color: {ACCENT_COLOR}; font-weight: 800; font-size: 12px; letter-spacing: 1px;")
        self.status_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lay.addWidget(self.status_msg)
        
        self.approval_container = QWidget()
        appr_lay = QHBoxLayout(self.approval_container)
        appr_lay.setContentsMargins(0, 0, 0, 0)
        appr_lay.setSpacing(12)
        
        btn_appr = QPushButton("AUTHORIZE ACTION")
        btn_appr.setObjectName("BtnApprove")
        btn_appr.setFixedHeight(38)
        btn_appr.clicked.connect(lambda: self.approval_given.emit(True))
        
        btn_rej = QPushButton("REJECT")
        btn_rej.setObjectName("BtnReject")
        btn_rej.setFixedHeight(38)
        btn_rej.clicked.connect(lambda: self.approval_given.emit(False))
        
        appr_lay.addWidget(btn_appr)
        appr_lay.addWidget(btn_rej)

        self.interaction_stack.addWidget(self.status_container)
        self.interaction_stack.addWidget(self.approval_container)
        layout.addWidget(self.interaction_stack)

        # --- 4. Semantic Log Area ---
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Streaming agent logic...")
        layout.addWidget(self.log_area)

        # --- 5. Unified Command Input ---
        cmd_layout = QHBoxLayout()
        cmd_layout.setSpacing(10)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type command for Arvyn...")
        self.input_field.returnPressed.connect(self._handle_submit)
        
        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setFixedSize(46, 46)
        # Dynamic Mic color logic (Green/Red)
        self.btn_mic.setStyleSheet("background-color: #ff3b30; border-radius: 23px; border: none; font-size: 20px;")
        self.btn_mic.clicked.connect(self._toggle_mic)

        cmd_layout.addWidget(self.input_field)
        cmd_layout.addWidget(self.btn_mic)
        layout.addLayout(cmd_layout)

    def _toggle_mic(self):
        """Toggles mic and updates visual state with dashboard logging."""
        if not self.is_listening:
            self.is_listening = True
            self.btn_mic.setStyleSheet("background-color: #4cd964; border-radius: 23px; border: none; font-size: 20px;")
            self.append_log("[VOICE] INITIALIZING CAPTURE LAYER", category="system")
        else:
            self.is_listening = False
            self.btn_mic.setStyleSheet("background-color: #ff3b30; border-radius: 23px; border: none; font-size: 20px;")
            self.append_log("[VOICE] PROCESSING AUDIO SEQUENCE", category="system")
            
        self.mic_clicked.emit(self.is_listening)

    def _handle_submit(self):
        text = self.input_field.text().strip()
        if text:
            self.command_submitted.emit(text)
            self.input_field.clear()

    def append_log(self, text: str, category: str = "general"):
        """Superior Semantic Logger with automatic keyword detection."""
        colors = {
            "action": ACCENT_COLOR,
            "system": "#888888",
            "error": ERROR_COLOR,
            "success": SUCCESS_COLOR,
            "kinetic": "#f1c40f",
            "general": "#e0e0e0"
        }
        
        # Semantic keyword routing
        text_lower = text.lower()
        if any(k in text_lower for k in ["[action]", "[brain]", "reasoning"]): category = "action"
        elif any(k in text_lower for k in ["[error]", "failed", "fault"]): category = "error"
        elif any(k in text_lower for k in ["completed", "success", "reached", "🏁"]): category = "success"
        elif any(k in text_lower for k in ["kinetic", "typing", "clicking"]): category = "kinetic"
        elif any(k in text_lower for k in ["[intent", "[discovery", "resolving"]): category = "system"

        color = colors.get(category, colors["general"])
        # Format with high-contrast timestamping if present
        formatted_text = f"<div style='margin-bottom: 5px;'><span style='color:{color}; font-weight:900;'>&gt;</span> {text}</div>"
        
        self.log_area.append(formatted_text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def update_screenshot(self, b64_data: str):
        """Syncs high-resolution visual feed to the monitor."""
        try:
            img_data = base64.b64decode(b64_data)
            image = QImage.fromData(img_data)
            pixmap = QPixmap.fromImage(image)
            
            # Smooth scaling optimized for the high-res 1080p source
            scaled_pixmap = pixmap.scaled(
                self.visual_monitor.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.visual_monitor.setPixmap(scaled_pixmap)
            self.status_msg.setText("EYES ON TARGET")
        except Exception as e:
            self.append_log(f"Feed Error: {e}", category="error")