import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QTextEdit, QPushButton, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from config import GLASS_STYLE, DASHBOARD_SIZE, logger

class ArvynDashboard(QMainWindow):
    """
    The Command Center. 
    Displays real-time logs and handles Human-in-the-Loop (HITL) approvals.
    """
    approval_granted = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arvyn Dashboard - System Logs")
        self.setFixedSize(*DASHBOARD_SIZE)
        self._setup_ui()
        
    def _setup_ui(self):
        """Builds the glass-morphic command interface."""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setStyleSheet(GLASS_STYLE)
        
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("SYSTEM OPERATIONAL LOGS")
        header.setStyleSheet("font-weight: bold; font-size: 14pt; letter-spacing: 2px;")
        layout.addWidget(header)

        # Terminal Output
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setPlaceholderText("Awaiting neural handshake...")
        layout.addWidget(self.log_viewer)

        # Action Area
        self.status_label = QLabel("Status: Standby")
        layout.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        
        self.approve_btn = QPushButton("APPROVE TRANSACTION")
        self.approve_btn.setEnabled(False) # Locked until Agent requests verification
        self.approve_btn.clicked.connect(self._handle_approval)
        
        self.close_btn = QPushButton("HIDE")
        self.close_btn.clicked.connect(self.hide)

        button_layout.addWidget(self.approve_btn)
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)

    def log_message(self, message: str, level: str = "INFO"):
        """Appends formatted messages to the glass terminal."""
        color = "#00FFCC" # Cyan for standard
        if level == "ERROR": color = "#FF5555"
        if level == "REASONING": color = "#BD93F9" # Purple

        formatted_msg = f'<span style="color:{color};">[{level}]</span> {message}'
        self.log_viewer.append(formatted_msg)
        # Auto-scroll to bottom
        self.log_viewer.verticalScrollBar().setValue(self.log_viewer.verticalScrollBar().maximum())

    def request_user_approval(self, detail: str):
        """Activates the safety guardrail for financial execution."""
        self.status_label.setText(f"Awaiting Verification: {detail}")
        self.approve_btn.setEnabled(True)
        self.approve_btn.setStyleSheet("background-color: rgba(0, 120, 212, 200); border: 2px solid white;")
        self.show() # Bring to front

    def _handle_approval(self):
        """Resumes the Agent thread after human verification."""
        self.log_message("Transaction verified by user. Resuming...", "SUCCESS")
        self.approve_btn.setEnabled(False)
        self.approve_btn.setStyleSheet("")
        self.status_label.setText("Status: Executing Approved Task")
        self.approval_granted.emit()