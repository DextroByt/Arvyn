import base64
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTextEdit, QStackedWidget, QFrame, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QImage, QColor

from config import (
    DASHBOARD_SIZE, 
    ACCENT_COLOR, 
    ERROR_COLOR, 
    SUCCESS_COLOR,
    STRICT_AUTONOMY_MODE
)

class ArvynDashboard(QFrame):
    """
    Superior Command Center for Agent Arvyn.
    UPGRADED: Features Autonomous Action Highlighting (Zero-Auth mode).
    FIXED: Real-time semantic logging for sensitive credential entry.
    RESIZED: Optimized for 350px width to prevent background UI occlusion.
    """
    command_submitted = pyqtSignal(str)
    mic_clicked = pyqtSignal(bool)
    approval_given = pyqtSignal(bool)
    minimize_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Dashboard")
        # Uses the optimized compact size (350, 620) from config.py
        self.setFixedSize(DASHBOARD_SIZE[0], DASHBOARD_SIZE[1]) 
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.is_listening = False
        
        self._init_styles()
        self._init_ui()

    def _init_styles(self):
        """Advanced Glass Morphism Stylesheet with semantic highlighting."""
        self.setStyleSheet(f"""
            #Dashboard {{
                background-color: rgba(15, 15, 20, 250);
                border: 1px solid rgba(0, 210, 255, 40);
                border-radius: 24px;
            }}
            QLabel {{ color: #ffffff; font-family: 'Segoe UI', sans-serif; }}
            
            QTextEdit {{
                background: rgba(0, 0, 0, 160);
                color: #d1d1d1;
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 12px;
                font-family: 'Consolas', 'Courier New';
                font-size: 10px;
                line-height: 1.4;
                padding: 8px;
            }}
            
            QLineEdit {{
                background: rgba(255, 255, 255, 8);
                color: #ffffff;
                border: 1px solid rgba(0, 210, 255, 30);
                border-radius: 18px;
                padding: 10px 14px;
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
            
            #BtnControl {{ background: transparent; border: none; font-size: 18px; color: #888; }}
            #BtnControl:hover {{ color: {ACCENT_COLOR}; }}
            #BtnStop:hover {{ color: {ERROR_COLOR}; }}
            
            #BtnApprove {{ background: rgba(46, 204, 113, 20); border-color: #2ecc71; color: #2ecc71; }}
            #BtnReject {{ background: rgba(231, 76, 60, 20); border-color: {ERROR_COLOR}; color: {ERROR_COLOR}; }}
            
            #VisualMonitor {{
                background: #000;
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 10px;
            }}
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(12)

        # --- 1. Header Area ---
        header_layout = QHBoxLayout()
        mode_suffix = "AUTO" if STRICT_AUTONOMY_MODE else "COMMAND"
        self.header = QLabel(f"ARVYN // {mode_suffix}")
        self.header.setStyleSheet(f"font-weight: 900; letter-spacing: 1.5px; font-size: 10px; color: {ACCENT_COLOR};")
        
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
        self.visual_monitor.setText("AWAITING FEED...")
        self.visual_monitor.setStyleSheet("color: #444; font-size: 9px; font-weight: bold;")
        layout.addWidget(self.visual_monitor)

        # --- 3. Interaction Status ---
        self.interaction_stack = QStackedWidget()
        self.interaction_stack.setFixedHeight(50)

        self.status_container = QWidget()
        status_lay = QVBoxLayout(self.status_container)
        status_lay.setContentsMargins(0, 0, 0, 0)
        initial_status = "AUTONOMOUS ENGINE ACTIVE" if STRICT_AUTONOMY_MODE else "SYSTEM STANDBY"
        self.status_msg = QLabel(initial_status)
        self.status_msg.setStyleSheet(f"color: {ACCENT_COLOR}; font-weight: 800; font-size: 11px; letter-spacing: 1px;")
        self.status_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lay.addWidget(self.status_msg)
        
        self.approval_container = QWidget()
        appr_lay = QHBoxLayout(self.approval_container)
        appr_lay.setContentsMargins(0, 0, 0, 0)
        appr_lay.setSpacing(10)
        
        # NOTE: These buttons are rarely shown in Zero-Auth mode but kept for visual-stuck fallback
        btn_appr = QPushButton("AUTHORIZE")
        btn_appr.setObjectName("BtnApprove")
        btn_appr.setFixedHeight(34)
        btn_appr.clicked.connect(lambda: self.approval_given.emit(True))
        
        btn_rej = QPushButton("REJECT")
        btn_rej.setObjectName("BtnReject")
        btn_rej.setFixedHeight(34)
        btn_rej.clicked.connect(lambda: self.approval_given.emit(False))
        
        appr_lay.addWidget(btn_appr)
        appr_lay.addWidget(btn_rej)

        self.interaction_stack.addWidget(self.status_container)
        self.interaction_stack.addWidget(self.approval_container)
        layout.addWidget(self.interaction_stack)

        # --- 4. Semantic Log Area ---
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Streaming autonomous logic...")
        layout.addWidget(self.log_area)

        # --- 5. Unified Command Input ---
        cmd_layout = QHBoxLayout()
        cmd_layout.setSpacing(8)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Direct command input...")
        self.input_field.returnPressed.connect(self._handle_submit)
        
        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setFixedSize(40, 40)
        self.btn_mic.setStyleSheet("background-color: #ff3b30; border-radius: 20px; border: none; font-size: 18px;")
        self.btn_mic.clicked.connect(self._toggle_mic)

        cmd_layout.addWidget(self.input_field)
        cmd_layout.addWidget(self.btn_mic)
        layout.addLayout(cmd_layout)

    def _toggle_mic(self):
        if not self.is_listening:
            self.is_listening = True
            self.btn_mic.setStyleSheet("background-color: #4cd964; border-radius: 20px; border: none; font-size: 18px;")
            self.append_log("[VOICE] MIC ACTIVE", category="system")
        else:
            self.is_listening = False
            self.btn_mic.setStyleSheet("background-color: #ff3b30; border-radius: 20px; border: none; font-size: 18px;")
            self.append_log("[VOICE] PROCESSING", category="system")
        self.mic_clicked.emit(self.is_listening)

    def _handle_submit(self):
        text = self.input_field.text().strip()
        if text:
            self.command_submitted.emit(text)
            self.input_field.clear()

    def append_log(self, text: str, category: str = "general"):
        """
        Semantic Log Streaming.
        IMPROVED: Added 'autonomous' category for Zero-Auth monitoring.
        """
        colors = {
            "action": ACCENT_COLOR,
            "system": "#888888",
            "error": ERROR_COLOR,
            "success": SUCCESS_COLOR,
            "kinetic": "#f1c40f",
            "autonomous": "#BB86FC", # NEW: High-vis Purple for autonomous actions
            "general": "#e0e0e0"
        }
        text_lower = text.lower()
        
        # Categorization Logic
        if any(k in text_lower for k in ["secure action", "autofill", "autonomous", "bypass"]): category = "autonomous"
        elif any(k in text_lower for k in ["[action]", "[brain]", "reasoning"]): category = "action"
        elif any(k in text_lower for k in ["[error]", "failed", "fault"]): category = "error"
        elif any(k in text_lower for k in ["completed", "success", "reached", "🏁"]): category = "success"
        elif any(k in text_lower for k in ["kinetic", "typing", "clicking"]): category = "kinetic"
        elif any(k in text_lower for k in ["[intent", "[discovery", "resolving"]): category = "system"

        color = colors.get(category, colors["general"])
        # Format with high-contrast prefix
        prefix = "⚡" if category == "autonomous" else "&gt;"
        formatted_text = f"<div style='margin-bottom: 4px;'><span style='color:{color}; font-weight:900;'>{prefix}</span> {text}</div>"
        
        self.log_area.append(formatted_text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def update_screenshot(self, b64_data: str):
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
            # Update Dashboard feedback
            if STRICT_AUTONOMY_MODE:
                self.status_msg.setText("AUTONOMOUS EXECUTION IN PROGRESS")
            else:
                self.status_msg.setText("EYES ON TARGET")
        except Exception as e:
            self.append_log(f"Feed Error: {e}", category="error")