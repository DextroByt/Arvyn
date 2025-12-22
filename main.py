import sys
import os
import asyncio
import logging
import traceback
from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QTimer

# Import upgraded config (v5.0 - QUBRID/QWEN3 integration)
from config import (
    Config, 
    logger, 
    ORB_SIZE, 
    DASHBOARD_SIZE, 
    STRICT_AUTONOMY_MODE, 
    AUTO_APPROVAL,
    QUBRID_MODEL_NAME
)

from gui.widget_orb import ArvynOrb
from gui.dashboard import ArvynDashboard
from gui.threads import AgentWorker, VoiceWorker
from tools.voice import ArvynVoice

def exception_hook(exctype, value, tb):
    """Global handler for FATAL UI errors."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"FATAL UI EXCEPTION:\n{err_msg}")
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook

class ArvynApp(ArvynOrb):
    """
    Superior Application Controller for Agent Arvyn (v5.0).
    v5.0 UPGRADE: Integrated Semantic Kinetic Engine for pixel-perfect anchoring.
    FIXED: Eliminates VLM coordinate drift via hidden DOM-Sync layer.
    IMPROVED: Enhanced status reporting for multi-layer kinetic interactions.
    PRESERVED: Full Qubrid/Qwen-3 Logic, VoiceWorker, and HITL approval flows.
    """
    def __init__(self):
        super().__init__()
        
        # --- PROJECT SPECIFIC PRIORITY MAP ---
        self.PROJECT_URL = "https://roshan-chaudhary13.github.io/rio_finance_bank/"
        self.PRIORITY_KEYWORDS = [
            "bill", "electricity", "gold", "profile", "login", 
            "bank", "rio", "loan", "account", "transfer", "pay",
            "balance", "statement", "credit", "debit"
        ]

        logger.info("[SYSTEM] Initializing Arvyn Integrity Check (v5.0)...")
        self.voice = ArvynVoice()
        self._is_expanded = False
        self.container = QStackedWidget()
        
        # UI Stack setup
        self.container.addWidget(self.status_label)
        self.dashboard = ArvynDashboard()
        self.container.addWidget(self.dashboard)
        self.layout.addWidget(self.container)

        # Worker initialization
        self.worker = AgentWorker() 
        self._connect_worker_signals()
        self.worker.start()

        self.voice_worker = None
        
        # UI Signal Connections
        self.clicked.connect(self.initiate_expansion)
        self.dashboard.command_submitted.connect(self.process_command)
        self.dashboard.mic_clicked.connect(self.trigger_voice_input)
        # Secondary mic (alternate capture mode)
        # self.dashboard.mic2_clicked.connect(self.trigger_voice_input)
        
        self.dashboard.approval_given.connect(self.handle_hitl_approval)
        self.dashboard.minimize_requested.connect(self.initiate_shrink)
        self.dashboard.stop_requested.connect(self.kill_agent)

        # Frameless Top-Hint Window settings
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.move_to_default_position()
        self.start_pulse()
        
        # v5.0 Initialization Reporting
        mode_label = "AUTONOMOUS" if STRICT_AUTONOMY_MODE else "HITL-STANDARD"
        logger.info(f"🛡️ Arvyn App v5.0: {mode_label} Controller ({QUBRID_MODEL_NAME}) active.")
        
        self.dashboard.append_log(f"SYSTEM: Environment Verified. Engine: {QUBRID_MODEL_NAME}", category="system")
        self.dashboard.append_log(f"SYSTEM: Semantic Kinetic Engine: v5.0 Focus-Lock Active.", category="system")
        self.dashboard.append_log(f"KINETIC: Hidden DOM manipulation & Visual Sync ENABLED.", category="kinetic")

    def _connect_worker_signals(self):
        """Maps backend worker signals to Dashboard UI updates."""
        self.worker.log_signal.connect(self.dashboard.append_log)
        self.worker.status_signal.connect(self._update_ui_status)
        self.worker.screenshot_signal.connect(self.dashboard.update_screenshot)
        self.worker.approval_signal.connect(self._toggle_approval_ui)
        self.worker.speak_signal.connect(self.voice.speak)
        self.worker.auto_mic_signal.connect(self._handle_auto_mic_logic)

    def _handle_auto_mic_logic(self, should_start: bool):
        """Triggers the microphone automatically after TTS sequences."""
        if should_start and not self.dashboard.is_listening:
            QTimer.singleShot(2200, self.dashboard._toggle_mic)

    def move_to_default_position(self):
        """Positions the Orb at the bottom-right of the screen."""
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - self.width() - 40
        y = screen.height() - self.height() - 40
        self.move(x, y)

    def initiate_expansion(self):
        """Animates the transition from Orb to Dashboard."""
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
        """Animates the transition from Dashboard back to Orb."""
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
        """Validates and applies priority routing for v5.0 tasks."""
        clean_text = command_text.strip().lower()
        if clean_text:
            self.dashboard.append_log(f"USER: {clean_text.upper()}", category="system")
            self.dashboard.input_field.clear()

            is_priority_task = any(key in clean_text for key in self.PRIORITY_KEYWORDS)

            if is_priority_task:
                self.dashboard.append_log(f"🎯 TARGET LOCKED: Rio Finance Bank", category="kinetic")
                self.dashboard.append_log(f"NETWORK: Semantic Sync active for portal interaction.", category="system")
                self.worker.submit_command(f"Open {self.PROJECT_URL} and {clean_text}")
            else:
                self.worker.submit_command(clean_text)

    def trigger_voice_input(self, should_start: bool):
        """Starts or stops the Voice Transcriber worker."""
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
            logger.info(f"🗣️ Transcribed: {text}")
            self.process_command(text)
        else:
            self._update_ui_status("Ready")

    def kill_agent(self):
        """Emergency release of all system resources."""
        logger.warning("🛑 Arvyn Main: Emergency shutdown initiated.")
        if self.worker and self.worker.isRunning():
            self.worker.stop_persistent_session()
            self._update_ui_status("STOPPED")
            self.dashboard.append_log("System: Deactivating Semantic Layer...", category="error")
            self.dashboard.append_log("System: Resources released.", category="error")
        QTimer.singleShot(1000, QApplication.instance().quit)

    def _update_ui_status(self, status: str):
        """Updates status labels on both Orb and Dashboard."""
        display_status = status.replace("_", " ").upper()
        self.dashboard.header.setText(f"ARVYN // {display_status}")
        self.status_label.setText(display_status)

    def _toggle_approval_ui(self, show: bool, force_manual: bool = False):
        """Handles manual approval requests or auto-approval bypass."""
        logger.info(f"🛡️ UI Approval Toggle: show={show}, force_manual={force_manual}")
        # CONCISE PAUSE FEATURE: Override auto-approval for security fields
        if show and force_manual:
             self.dashboard.append_log("🛡️ SECURITY LOCK: Manual approval required for PIN/Payment.", category="kinetic")
             self.dashboard.interaction_stack.setCurrentIndex(1)
             self.activateWindow()
             return

        if AUTO_APPROVAL and show:
            self.handle_hitl_approval(True)
            return

        self.dashboard.interaction_stack.setCurrentIndex(1 if show else 0)
        if show:
            self.activateWindow()
            self.dashboard.append_log("NOTIFICATION: Semantic Sync requires manual verification.", category="kinetic")

    def handle_hitl_approval(self, approved: bool):
        """Signals the worker to resume or abort based on user input."""
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