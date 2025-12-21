import sys
import os
import asyncio
import logging
import traceback
from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QTimer

# Import upgraded config (renamed QWEN to QUBRID)
from config import (
    Config, 
    logger, 
    ORB_SIZE, 
    DASHBOARD_SIZE, 
    STRICT_AUTONOMY_MODE, 
    AUTO_APPROVAL,
    QUBRID_MODEL_NAME  # Updated import
)

from gui.widget_orb import ArvynOrb
from gui.dashboard import ArvynDashboard
from gui.threads import AgentWorker, VoiceWorker
from tools.voice import ArvynVoice

def exception_hook(exctype, value, tb):
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"FATAL UI EXCEPTION:\n{err_msg}")
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook

class ArvynApp(ArvynOrb):
    """
    Superior Application Controller for Agent Arvyn.
    UPGRADED: Features Qubrid-powered Qwen-3 Logic.
    FIXED: Forced Priority Routing for Rio Finance Bank tasks.
    """
    def __init__(self):
        super().__init__()
        
        # --- IMPROVEMENT: PROJECT SPECIFIC PRIORITY MAP ---
        # This prevents the AI from searching Google for these tasks.
        self.PROJECT_URL = "https://roshan-chaudhary13.github.io/rio_finance_bank/"
        self.PRIORITY_KEYWORDS = ["bill", "electricity", "gold", "profile", "login", "bank"]

        self.voice = ArvynVoice()
        self._is_expanded = False
        self.container = QStackedWidget()
        
        self.container.addWidget(self.status_label)
        self.dashboard = ArvynDashboard()
        self.container.addWidget(self.dashboard)
        self.layout.addWidget(self.container)

        self.worker = AgentWorker() 
        self._connect_worker_signals()
        self.worker.start()

        self.voice_worker = None
        
        self.clicked.connect(self.initiate_expansion)
        self.dashboard.command_submitted.connect(self.process_command)
        self.dashboard.mic_clicked.connect(self.trigger_voice_input)
        self.dashboard.approval_given.connect(self.handle_hitl_approval)
        self.dashboard.minimize_requested.connect(self.initiate_shrink)
        self.dashboard.stop_requested.connect(self.kill_agent)

        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.move_to_default_position()
        self.start_pulse()
        
        mode_label = "AUTONOMOUS" if STRICT_AUTONOMY_MODE else "HITL-STANDARD"
        # Updated log to show Qubrid Engine info
        logger.info(f"🛡️ Arvyn App v4.5: {mode_label} Controller ({QUBRID_MODEL_NAME}) active.")
        self.dashboard.append_log(f"SYSTEM: Initialized with Qwen Engine via Qubrid Serverless.", category="system")

    def _connect_worker_signals(self):
        self.worker.log_signal.connect(self.dashboard.append_log)
        self.worker.status_signal.connect(self._update_ui_status)
        self.worker.screenshot_signal.connect(self.dashboard.update_screenshot)
        self.worker.approval_signal.connect(self._toggle_approval_ui)
        self.worker.speak_signal.connect(self.voice.speak)
        self.worker.auto_mic_signal.connect(self._handle_auto_mic_logic)

    def _handle_auto_mic_logic(self, should_start: bool):
        if should_start and not self.dashboard.is_listening:
            QTimer.singleShot(2000, self.dashboard._toggle_mic)

    def move_to_default_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - self.width() - 40
        y = screen.height() - self.height() - 40
        self.move(x, y)

    def initiate_expansion(self):
        if not self._is_expanded:
            self._is_expanded = True
            self.stop_pulse()
            self.anim = QPropertyAnimation(self, b"geometry")
            self.anim.setDuration(450)
            self.anim.setStartValue(self.geometry())
            screen = QApplication.primaryScreen().availableGeometry()
            new_rect = QRect(
                screen.width() - DASHBOARD_SIZE[0] - 40,
                screen.height() - DASHBOARD_SIZE[1] - 40,
                DASHBOARD_SIZE[0],
                DASHBOARD_SIZE[1]
            )
            self.anim.setEndValue(new_rect)
            self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim.finished.connect(self._switch_to_dashboard_view)
            self.anim.start()

    def initiate_shrink(self):
        if self._is_expanded:
            self._is_expanded = False
            self.container.setCurrentIndex(0)
            self.anim = QPropertyAnimation(self, b"geometry")
            self.anim.setDuration(400)
            self.anim.setStartValue(self.geometry())
            screen = QApplication.primaryScreen().availableGeometry()
            new_rect = QRect(
                screen.width() - ORB_SIZE - 40,
                screen.height() - ORB_SIZE - 40,
                ORB_SIZE,
                ORB_SIZE
            )
            self.anim.setEndValue(new_rect)
            self.anim.setEasingCurve(QEasingCurve.Type.InCubic)
            self.anim.finished.connect(self.start_pulse)
            self.anim.start()

    def _switch_to_dashboard_view(self):
        self.container.setCurrentIndex(1)
        self.dashboard.input_field.setFocus()

    def process_command(self, command_text: str):
        """Validates and applies priority routing for bank-specific tasks."""
        clean_text = command_text.strip().lower()
        if clean_text:
            self.dashboard.append_log(f"USER: {clean_text.upper()}", category="system")
            self.dashboard.input_field.clear()

            # 1. Check if the command involves your project tasks
            is_priority_task = any(key in clean_text for key in self.PRIORITY_KEYWORDS)

            if is_priority_task:
                self.dashboard.append_log(f"🎯 TARGET LOCKED: Rio Finance Bank", category="kinetic")
                # We inject the URL directly into the worker to bypass Google search
                self.worker.submit_command(f"Open {self.PROJECT_URL} and {clean_text}")
            else:
                # Normal AI processing for other general tasks
                self.worker.submit_command(clean_text)

    def trigger_voice_input(self, should_start: bool):
        if should_start:
            if self.voice_worker and self.voice_worker.isRunning():
                return
            self.voice_worker = VoiceWorker()
            self.voice_worker.text_received.connect(self._handle_voice_success)
            self.voice_worker.status_signal.connect(self._update_ui_status)
            self.voice_worker.start()
        else:
            if self.voice_worker and self.voice_worker.isRunning():
                self.voice_worker.stop()

    def _handle_voice_success(self, text):
        if text:
            self.process_command(text)
        else:
            self._update_ui_status("Ready")

    def kill_agent(self):
        logger.warning("🛑 Arvyn Main: Emergency shutdown initiated.")
        if self.worker and self.worker.isRunning():
            self.worker.stop_persistent_session()
            self._update_ui_status("STOPPED")
            self.dashboard.append_log("System: Resources released.", category="error")
        QTimer.singleShot(1000, QApplication.instance().quit)

    def _update_ui_status(self, status: str):
        display_status = status.replace("_", " ").upper()
        self.dashboard.header.setText(f"ARVYN // {display_status}")
        self.status_label.setText(display_status)

    def _toggle_approval_ui(self, show: bool):
        if AUTO_APPROVAL and show:
            self.handle_hitl_approval(True)
            return

        self.dashboard.interaction_stack.setCurrentIndex(1 if show else 0)
        if show:
            self.activateWindow()
            self.dashboard.append_log("NOTIFICATION: Processing autonomously...", category="kinetic")

    def handle_hitl_approval(self, approved: bool):
        if self.worker:
            self.worker.resume_with_approval(approved)

if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    try:
        arvyn = ArvynApp()
        arvyn.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Arvyn Core Fatal Error: {e}")
        sys.exit(1)