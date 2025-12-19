import sys
import asyncio
import logging
from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QRect, QEasingCurve

# Import config first to initialize logging correctly
from config import Config, logger, ORB_SIZE, DASHBOARD_SIZE

from gui.widget_orb import ArvynOrb
from gui.dashboard import ArvynDashboard
from gui.threads import AgentWorker, VoiceWorker 

class ArvynApp(ArvynOrb):
    """
    The Core Application Controller (Production Grade).
    Manages persistent browser sessions and the Toggle-to-Talk lifecycle.
    """
    def __init__(self):
        super().__init__()
        self.worker = None
        self.voice_worker = None
        self._is_expanded = False
        
        # Setup Internal View Switching
        self.container = QStackedWidget()
        
        # Index 0: The Status Label (from ArvynOrb)
        self.container.addWidget(self.status_label)
        
        # Index 1: The Dashboard
        self.dashboard = ArvynDashboard()
        self.container.addWidget(self.dashboard)
        
        self.layout.addWidget(self.container)
        
        # Signal Connections
        self.clicked.connect(self.initiate_expansion)
        self.dashboard.command_submitted.connect(self.process_command)
        self.dashboard.mic_clicked.connect(self.trigger_voice_input)
        self.dashboard.approval_given.connect(self.handle_hitl_approval)
        self.dashboard.minimize_requested.connect(self.initiate_shrink)
        self.dashboard.stop_requested.connect(self.kill_agent)

        self.move_to_default_position()
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.start_pulse()
        
        logger.info("Agent Arvyn Production Core initialized with session persistence.")

    def move_to_default_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - self.width() - 40
        y = screen.height() - self.height() - 40
        self.move(x, y)

    def initiate_expansion(self):
        """Animates morphing from Orb into the Dashboard."""
        if not self._is_expanded:
            self._is_expanded = True
            self.stop_pulse()
            
            self.anim = QPropertyAnimation(self, b"geometry")
            self.anim.setDuration(400)
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
        """Animates dashboard back down into the small Orb."""
        if self._is_expanded:
            self._is_expanded = False
            self.container.setCurrentIndex(0)
            
            self.anim = QPropertyAnimation(self, b"geometry")
            self.anim.setDuration(350)
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
        """
        Handles command processing. 
        Will overwrite existing persistent sessions if a new command is issued.
        """
        # If a worker is running but in a persistent 'Ready' state, we stop it 
        # to clear the old session before starting a new one.
        if self.worker and self.worker.isRunning():
            logger.info("Overwriting previous persistent session for new command.")
            self.worker.stop()
            self.worker.wait(500)

        logger.info(f"Command Input: {command_text}")
        self.worker = AgentWorker(command_text)
        self.worker.log_signal.connect(self.dashboard.append_log)
        self.worker.status_signal.connect(self._update_ui_status)
        self.worker.screenshot_signal.connect(self.dashboard.update_screenshot)
        self.worker.approval_signal.connect(self._toggle_approval_ui)
        self.worker.start()

    def trigger_voice_input(self, should_start: bool):
        """Handles Toggle-to-Talk logic from Dashboard mic button."""
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
            self.dashboard.input_field.setText(text)
            self.process_command(text)
        else:
            self.dashboard.append_log("No speech detected.")
            self._update_ui_status("Ready")

    def kill_agent(self):
        """
        The only way to explicitly close the persistent browser session.
        This triggers the orchestrator's cleanup() via the worker's thread exit.
        """
        if self.worker and self.worker.isRunning():
            logger.warning("Agent execution and browser session killed by user.")
            self.worker.stop()
            self.worker.wait(1000)
            if self.worker.isRunning():
                self.worker.terminate()
            self._update_ui_status("Stopped")
            self.dashboard.append_log("Browser resources released.")
        else:
            self.dashboard.append_log("No active session to stop.")

    def _update_ui_status(self, status: str):
        self.dashboard.header.setText(f"ARVYN: {status.upper()}")
        self.status_label.setText(status)

    def _toggle_approval_ui(self, show: bool):
        if show:
            self.dashboard.interaction_stack.setCurrentIndex(1)
            self.activateWindow()
        else:
            self.dashboard.interaction_stack.setCurrentIndex(0)

    def handle_hitl_approval(self, approved: bool):
        if self.worker:
            self.worker.resume_with_approval(approved)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        arvyn = ArvynApp()
        arvyn.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"App Crash: {e}")
        sys.exit(1)