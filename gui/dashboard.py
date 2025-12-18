from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from qframelesswindow import AcrylicWindow
from config import DASHBOARD_SIZE, GLASS_STYLE, ACCENT_COLOR

class ArvynDashboard(AcrylicWindow):
    # Signals to communicate back to the main controller
    input_submitted = pyqtSignal(str)
    approval_granted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._setup_window()
        self._init_ui()
        self.set_status("Ready for Command")

    def _setup_window(self):
        """Configures the Acrylic Glass effect and dimensions."""
        self.setWindowTitle("Arvyn Command Center")
        self.setFixedSize(DASHBOARD_SIZE[0], DASHBOARD_SIZE[1])
        self.windowEffect.setAcrylicEffect(self.winId(), "1E1E1E99")
        self.setStyleSheet(GLASS_STYLE)

    def _init_ui(self):
        """Creates the layout including the Log area and Input/Approval controls."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 40, 20, 20) # Space for title bar

        # 1. Header & Status
        self.status_label = QLabel("STATUS: IDLE")
        self.status_label.setStyleSheet(f"color: {ACCENT_COLOR}; font-weight: bold; font-size: 14px;")
        main_layout.addWidget(self.status_label)

        # 2. Activity Log (Glass-style Text Edit)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Agent Arvyn Activity Log...")
        main_layout.addWidget(self.log_area)

        # 3. Input Zone (For missing data requests)
        self.input_frame = QFrame()
        input_layout = QHBoxLayout(self.input_frame)
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Provide data here...")
        self.user_input.returnPressed.connect(self._on_input_submit)
        
        self.submit_btn = QPushButton("Submit")
        self.submit_btn.clicked.connect(self._on_input_submit)
        
        input_layout.addWidget(self.user_input)
        input_layout.addWidget(self.submit_btn)
        self.input_frame.hide() # Hidden by default until agent requests data
        main_layout.addWidget(self.input_frame)

        # 4. Approval Zone (The Final Guardrail)
        self.approval_frame = QFrame()
        approval_layout = QVBoxLayout(self.approval_frame)
        
        self.approval_msg = QLabel("Verification Required")
        self.approve_btn = QPushButton("APPROVE TRANSACTION")
        self.approve_btn.setStyleSheet(f"background-color: {ACCENT_COLOR}; color: white; padding: 10px; font-weight: bold;")
        self.approve_btn.clicked.connect(lambda: self.approval_granted.emit("APPROVE"))
        
        approval_layout.addWidget(self.approval_msg)
        approval_layout.addWidget(self.approve_btn)
        self.approval_frame.hide() # Hidden by default
        main_layout.addWidget(self.approval_frame)

    # ==========================================
    # UI UPDATE METHODS
    # ==========================================
    def log(self, message: str):
        """Appends a timestamped message to the dashboard log."""
        self.log_area.append(f"<span style='color: #888888;'>[LOG]:</span> {message}")

    def set_status(self, status: str):
        """Updates the top-level status indicator."""
        self.status_label.setText(f"STATUS: {status.upper()}")
        self.log(status)

    def request_input(self, field_name: str):
        """Displays the input field for specific missing data."""
        self.input_frame.show()
        self.user_input.setPlaceholderText(f"Enter {field_name}...")
        self.user_input.setFocus()
        self.log(f"Arvyn is waiting for: {field_name}")

    def request_approval(self, detail: str):
        """Displays the big blue button for final confirmation."""
        self.approval_frame.show()
        self.approval_msg.setText(detail)
        self.log("Action paused for final approval.")

    def _on_input_submit(self):
        text = self.user_input.text()
        if text:
            self.input_submitted.emit(text)
            self.user_input.clear()
            self.input_frame.hide()

    def reset_controls(self):
        """Hides all action frames after task completion."""
        self.input_frame.hide()
        self.approval_frame.hide()