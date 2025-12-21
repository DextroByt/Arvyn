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
    Superior Command Center for Agent Arvyn (v4.8 - Precision Suite).
    UPGRADED: Multi-Layer Semantic Logging (Kinetic Sync monitoring).
    FIXED: Resolves feed latency by synchronizing status updates with v4.8 Browser logic.
    PRESERVED: All Glass-Morphism styles and Zero-Auth flow controls.
    """
    command_submitted = pyqtSignal(str)
    mic_clicked = pyqtSignal(bool)
    mic2_clicked = pyqtSignal(bool)
    chat_submitted = pyqtSignal(str)
    approval_given = pyqtSignal(bool)
    session_info_submitted = pyqtSignal(str, str)
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
        """Advanced Glass Morphism Stylesheet with semantic v4.8 highlighting."""
        self.setStyleSheet(f"""
            #Dashboard {{
                background-color: rgba(15, 15, 20, 252);
                border: 1px solid rgba(0, 210, 255, 45);
                border-radius: 24px;
            }}
            QLabel {{ color: #ffffff; font-family: 'Segoe UI', sans-serif; }}
            
            QTextEdit {{
                background: rgba(0, 0, 0, 180);
                color: #d1d1d1;
                border: 1px solid rgba(255, 255, 255, 12);
                border-radius: 12px;
                font-family: 'Consolas', 'Courier New';
                font-size: 10px;
                line-height: 1.5;
                padding: 10px;
            }}
            
            QLineEdit {{
                background: rgba(255, 255, 255, 10);
                color: #ffffff;
                border: 1px solid rgba(0, 210, 255, 35);
                border-radius: 18px;
                padding: 10px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT_COLOR}; background: rgba(0, 210, 255, 15); }}

            QPushButton {{
                background: rgba(0, 210, 255, 25);
                color: {ACCENT_COLOR};
                border: 1px solid rgba(0, 210, 255, 45);
                border-radius: 10px;
                font-weight: bold;
                font-size: 10px;
                text-transform: uppercase;
            }}
            QPushButton:hover {{ background: rgba(0, 210, 255, 50); color: white; }}
            
            #BtnControl {{ background: transparent; border: none; font-size: 18px; color: #999; }}
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
        layout.setContentsMargins(20, 18, 20, 22)
        layout.setSpacing(14)

        # --- 1. Header Area ---
        header_layout = QHBoxLayout()
        mode_suffix = "AUTO-V4.8" if STRICT_AUTONOMY_MODE else "COMMAND-V4.8"
        self.header = QLabel(f"ARVYN // {mode_suffix}")
        self.header.setStyleSheet(f"font-weight: 900; letter-spacing: 2px; font-size: 11px; color: {ACCENT_COLOR};")
        
        btn_min = QPushButton("−")
        btn_min.setObjectName("BtnControl")
        btn_min.setFixedSize(30, 30)
        btn_min.clicked.connect(self.minimize_requested.emit)

        btn_stop = QPushButton("×")
        btn_stop.setObjectName("BtnControl")
        btn_stop.setObjectName("BtnStop")
        btn_stop.setFixedSize(30, 30)
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
        self.visual_monitor.setText("AWAITING PRECISION FEED...")
        self.visual_monitor.setStyleSheet("color: #555; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(self.visual_monitor)

        # --- 2b. Session Panel (compact) ---
        self.session_panel = QFrame()
        self.session_panel.setObjectName("SessionPanel")
        self.session_panel.setFixedSize(310, 110)
        sp_layout = QVBoxLayout(self.session_panel)
        sp_layout.setContentsMargins(8, 8, 8, 8)
        sp_layout.setSpacing(6)

        self.session_title = QLabel("Active Session: None")
        self.session_title.setStyleSheet("font-weight:700; color: #ffffff; font-size: 11px;")
        sp_layout.addWidget(self.session_title)

        self.session_info_input = QLineEdit()
        self.session_info_input.setPlaceholderText("Provide missing info (key:value)...")
        sp_layout.addWidget(self.session_info_input)

        btn_row = QHBoxLayout()
        self.btn_session_submit = QPushButton("Provide")
        self.btn_session_submit.setFixedHeight(32)
        self.btn_session_submit.clicked.connect(self._submit_session_info)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_session_submit)
        sp_layout.addLayout(btn_row)

        self.session_panel.setStyleSheet("background: rgba(0,0,0,0.25); border-radius: 10px; border: 1px solid rgba(255,255,255,10);")
        layout.addWidget(self.session_panel)

        # --- 3. Interaction Status ---
        self.interaction_stack = QStackedWidget()
        self.interaction_stack.setFixedHeight(55)

        self.status_container = QWidget()
        status_lay = QVBoxLayout(self.status_container)
        status_lay.setContentsMargins(0, 0, 0, 0)
        initial_status = "PRECISION KINETIC ENGINE ACTIVE" if STRICT_AUTONOMY_MODE else "SYSTEM IDLE // STANDBY"
        self.status_msg = QLabel(initial_status)
        self.status_msg.setStyleSheet(f"color: {ACCENT_COLOR}; font-weight: 800; font-size: 11px; letter-spacing: 1px;")
        self.status_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lay.addWidget(self.status_msg)
        
        self.approval_container = QWidget()
        appr_lay = QHBoxLayout(self.approval_container)
        appr_lay.setContentsMargins(0, 0, 0, 0)
        appr_lay.setSpacing(12)
        
        # NOTE: Authorized buttons preserved for fallback scenarios
        btn_appr = QPushButton("AUTHORIZE")
        btn_appr.setObjectName("BtnApprove")
        btn_appr.setFixedHeight(36)
        btn_appr.clicked.connect(lambda: self.approval_given.emit(True))
        
        btn_rej = QPushButton("REJECT")
        btn_rej.setObjectName("BtnReject")
        btn_rej.setFixedHeight(36)
        btn_rej.clicked.connect(lambda: self.approval_given.emit(False))
        
        appr_lay.addWidget(btn_appr)
        appr_lay.addWidget(btn_rej)

        self.interaction_stack.addWidget(self.status_container)
        self.interaction_stack.addWidget(self.approval_container)
        layout.addWidget(self.interaction_stack)

        # --- 4. Semantic Log Area ---
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Streaming precision autonomous logic...")
        layout.addWidget(self.log_area)

        # --- 4b. Agent Chat Input (real-time chat) ---
        chat_layout = QHBoxLayout()
        chat_layout.setSpacing(8)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Chat with Arvyn (agent conversation)...")
        self.chat_input.returnPressed.connect(self._handle_chat_submit)

        self.chat_mic = QPushButton("🗨️")
        self.chat_mic.setFixedSize(40, 40)
        self.chat_mic.setStyleSheet("background-color: #6a5acd; border-radius: 20px; border: none; font-size: 16px;")
        self.chat_mic.clicked.connect(lambda: self.chat_submitted.emit(self.chat_input.text().strip()))

        chat_layout.addWidget(self.chat_input)
        chat_layout.addWidget(self.chat_mic)
        layout.addLayout(chat_layout)

        # --- 5. Unified Command Input ---
        cmd_layout = QHBoxLayout()
        cmd_layout.setSpacing(10)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Direct command input...")
        self.input_field.returnPressed.connect(self._handle_submit)
        
        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setFixedSize(42, 42)
        self.btn_mic.setStyleSheet("background-color: #ff3b30; border-radius: 21px; border: none; font-size: 20px;")
        self.btn_mic.clicked.connect(self._toggle_mic)

        self.btn_mic2 = QPushButton("🎧")
        self.btn_mic2.setFixedSize(42, 42)
        self.btn_mic2.setStyleSheet("background-color: #1e90ff; border-radius: 21px; border: none; font-size: 18px;")
        self.btn_mic2.clicked.connect(self._toggle_mic2)

        cmd_layout.addWidget(self.input_field)
        cmd_layout.addWidget(self.btn_mic2)
        cmd_layout.addWidget(self.btn_mic)
        layout.addLayout(cmd_layout)

    def _toggle_mic(self):
        if not self.is_listening:
            self.is_listening = True
            self.btn_mic.setStyleSheet("background-color: #4cd964; border-radius: 21px; border: none; font-size: 20px;")
            self.append_log("[VOICE] MIC ACTIVE - LISTENING", category="system")
        else:
            self.is_listening = False
            self.btn_mic.setStyleSheet("background-color: #ff3b30; border-radius: 21px; border: none; font-size: 20px;")
            self.append_log("[VOICE] ANALYZING SEQUENCE", category="system")
        self.mic_clicked.emit(self.is_listening)

    def _toggle_mic2(self):
        # Secondary mic — emits separate signal for alternate capture mode
        if not getattr(self, 'is_listening2', False):
            self.is_listening2 = True
            self.btn_mic2.setStyleSheet("background-color: #4cd964; border-radius: 21px; border: none; font-size: 18px;")
            self.append_log("[VOICE] ALT MIC ACTIVE - LISTENING", category="system")
        else:
            self.is_listening2 = False
            self.btn_mic2.setStyleSheet("background-color: #1e90ff; border-radius: 21px; border: none; font-size: 18px;")
            self.append_log("[VOICE] ALT MIC STOPPED", category="system")
        self.mic2_clicked.emit(getattr(self, 'is_listening2', False))

    def _submit_session_info(self):
        session_name = self.session_title.text().replace('Active Session: ', '')
        info_text = self.session_info_input.text().strip()
        if session_name and info_text:
            self.append_log(f"Session info submitted for {session_name}", category="autonomous")
            self.session_info_submitted.emit(session_name, info_text)
            self.session_info_input.clear()

    def set_active_session(self, session_name: str, missing_info: str = ''):
        self.session_title.setText(f"Active Session: {session_name}")
        self.session_info_input.setText(missing_info)

    def _handle_chat_submit(self):
        text = self.chat_input.text().strip()
        if text:
            self.chat_submitted.emit(text)
            self.chat_input.clear()
            self.append_log(f"CHAT SENT: {text}", category="discovery")

    def _handle_submit(self):
        text = self.input_field.text().strip()
        if text:
            self.command_submitted.emit(text)
            self.input_field.clear()

    def append_log(self, text: str, category: str = "general"):
        """
        Superior Semantic Log Streaming (v4.8).
        IMPROVED: Added 'precision' and 'discovery' categories for Multi-Layer tracking.
        """
        colors = {
            "action": ACCENT_COLOR,
            "system": "#999999",
            "error": ERROR_COLOR,
            "success": SUCCESS_COLOR,
            "kinetic": "#f1c40f",
            "precision": "#00d2ff", # High-vis Blue for coordinate sync
            "discovery": "#9b59b6", # Amethyst for site resolution
            "autonomous": "#BB86FC", # Purple for zero-auth actions
            "general": "#e0e0e0"
        }
        text_lower = text.lower()
        
        # Enhanced v4.8 Categorization Logic
        if any(k in text_lower for k in ["secure action", "autofill", "autonomous", "bypass"]): category = "autonomous"
        elif any(k in text_lower for k in ["precision", "offset", "sync", "stabiliz"]): category = "precision"
        elif any(k in text_lower for k in ["discovery", "resolving", "portal"]): category = "discovery"
        elif any(k in text_lower for k in ["[action]", "[brain]", "reasoning"]): category = "action"
        elif any(k in text_lower for k in ["[error]", "failed", "fault", "missed"]): category = "error"
        elif any(k in text_lower for k in ["completed", "success", "reached", "🏁"]): category = "success"
        elif any(k in text_lower for k in ["kinetic", "typing", "clicking", "interaction"]): category = "kinetic"
        elif any(k in text_lower for k in ["[intent", "system"]): category = "system"

        color = colors.get(category, colors["general"])
        # v4.8 prefix system
        prefixes = {
            "autonomous": "⚡",
            "precision": "🎯",
            "kinetic": "⚙️",
            "error": "❌",
            "success": "✅",
            "discovery": "🌐"
        }
        prefix = prefixes.get(category, "&gt;")
        formatted_text = f"<div style='margin-bottom: 5px;'><span style='color:{color}; font-weight:900;'>{prefix}</span> {text}</div>"
        
        self.log_area.append(formatted_text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def update_screenshot(self, b64_data: str):
        """Refreshes the precision visual monitor and status text."""
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
            
            # Context-Aware Status Feedback
            if STRICT_AUTONOMY_MODE:
                status_txt = "AUTONOMOUS EXECUTION // SYNCED"
                # Check for stabilization in recent logs
                if "stabilizing" in self.log_area.toPlainText().lower().split('\n')[-2:]:
                    status_txt = "STABILIZING UI FOR PRECISION..."
                self.status_msg.setText(status_txt)
            else:
                self.status_msg.setText("LIVE MONITORING // PRECISION FEED")
        except Exception as e:
            self.append_log(f"Feed Synchronization Error: {e}", category="error")