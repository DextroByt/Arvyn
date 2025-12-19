from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTextEdit, QStackedWidget, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon

class ArvynDashboard(QFrame):
    """
    Simplified Dashboard for Agent Arvyn.
    Provides direct control, activity logs, and HITL interaction.
    """
    command_submitted = pyqtSignal(str)
    mic_clicked = pyqtSignal()
    approval_given = pyqtSignal(bool)
    minimize_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Dashboard")
        self.setFixedSize(400, 500)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # Glass Morphism Styling
        self.setStyleSheet("""
            #Dashboard {
                background-color: rgba(20, 20, 25, 240);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 20px;
            }
            QLabel { color: white; font-family: 'Segoe UI'; }
            QTextEdit {
                background: rgba(0, 0, 0, 80);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 10px;
                font-size: 12px;
                padding: 10px;
            }
            QLineEdit {
                background: rgba(255, 255, 255, 10);
                color: white;
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 15px;
                padding: 10px 15px;
                font-size: 13px;
            }
            QPushButton {
                background: rgba(0, 210, 255, 40);
                color: white;
                border: 1px solid #00d2ff;
                border-radius: 10px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: rgba(0, 210, 255, 80); }
            
            #BtnControl { background: transparent; border: none; font-size: 18px; color: #aaa; }
            #BtnControl:hover { color: white; }
            #BtnStop:hover { color: #ff4b2b; }
            
            #BtnApprove { background: rgba(46, 204, 113, 30); border-color: #2ecc71; color: #2ecc71; }
            #BtnReject { background: rgba(231, 76, 60, 30); border-color: #e74c3c; color: #e74c3c; }
            #BtnApprove:hover { background: rgba(46, 204, 113, 60); }
            #BtnReject:hover { background: rgba(231, 76, 60, 60); }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(15)

        # --- 1. Title Bar ---
        header_layout = QHBoxLayout()
        self.header = QLabel("ARVYN: READY")
        self.header.setStyleSheet("font-weight: bold; letter-spacing: 1px; color: #00d2ff;")
        
        # Control Buttons (Minimize & Stop)
        btn_min = QPushButton("−")
        btn_min.setObjectName("BtnControl")
        btn_min.setFixedSize(30, 30)
        btn_min.clicked.connect(self.minimize_requested.emit)

        btn_stop = QPushButton("×")
        btn_stop.setObjectName("BtnControl")
        btn_stop.setFixedSize(30, 30)
        btn_stop.setObjectName("BtnStop")
        btn_stop.clicked.connect(self.stop_requested.emit)
        
        header_layout.addWidget(self.header)
        header_layout.addStretch()
        header_layout.addWidget(btn_min)
        header_layout.addWidget(btn_stop)
        layout.addLayout(header_layout)

        # --- 2. Interaction Area (HITL) ---
        self.interaction_stack = QStackedWidget()
        self.interaction_stack.setFixedHeight(70)

        # Default: Status Message
        self.status_container = QWidget()
        status_lay = QVBoxLayout(self.status_container)
        status_lay.setContentsMargins(0, 0, 0, 0)
        self.status_msg = QLabel("Ready for your command.")
        self.status_msg.setStyleSheet("color: #777; font-style: italic;")
        self.status_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lay.addWidget(self.status_msg)
        
        # Approval View (Appears when Agent needs permission)
        self.approval_container = QWidget()
        appr_lay = QHBoxLayout(self.approval_container)
        appr_lay.setContentsMargins(0, 5, 0, 5)
        appr_lay.setSpacing(15)
        
        btn_appr = QPushButton("APPROVE")
        btn_appr.setObjectName("BtnApprove")
        btn_appr.clicked.connect(lambda: self.approval_given.emit(True))
        
        btn_rej = QPushButton("REJECT")
        btn_rej.setObjectName("BtnReject")
        btn_rej.clicked.connect(lambda: self.approval_given.emit(False))
        
        appr_lay.addWidget(btn_appr)
        appr_lay.addWidget(btn_rej)

        self.interaction_stack.addWidget(self.status_container)
        self.interaction_stack.addWidget(self.approval_container)
        layout.addWidget(self.interaction_stack)

        # --- 3. Activity Logs ---
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Agent logs will stream here...")
        layout.addWidget(self.log_area)

        # --- 4. Command Input Bar ---
        cmd_layout = QHBoxLayout()
        cmd_layout.setSpacing(10)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Direct command (e.g., 'Pay Rio Bank 500')")
        self.input_field.returnPressed.connect(self._handle_submit)
        
        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setFixedSize(44, 44)
        self.btn_mic.setStyleSheet("border-radius: 22px; font-size: 18px;")
        self.btn_mic.clicked.connect(self.mic_clicked.emit)

        cmd_layout.addWidget(self.input_field)
        cmd_layout.addWidget(self.btn_mic)
        layout.addLayout(cmd_layout)

    def _handle_submit(self):
        text = self.input_field.text().strip()
        if text:
            self.command_submitted.emit(text)
            self.input_field.clear()

    def append_log(self, text: str):
        """Standardized logging for the UI console."""
        self.log_area.append(f"<span style='color:#00d2ff;'>&gt;</span> {text}")
        # Auto-scroll
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def update_screenshot(self, b64_data: str):
        """Updates internal status when browser captures visual state."""
        self.append_log("<i style='color:#666;'>[Visual Context Updated]</i>")