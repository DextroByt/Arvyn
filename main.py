import sys
import asyncio
import logging
from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QRect, QEasingCurve

# Import config first to initialize logging correctly
from config import Config, logger

# UI Constants (Adjust these as needed for your screen)
ORB_SIZE = 80
DASHBOARD_SIZE = (400, 500)

from gui.widget_orb import ArvynOrb
from gui.dashboard import ArvynDashboard
from gui.threads import AgentWorker
from tools.voice import ArvynVoice

class VoiceWorker(QThread):
    """Dedicated thread for voice recognition to avoid blocking the UI loop."""
    text_received = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, voice_tool):
        super().__init__()
        self.voice = voice_tool
        self._is_active = True

    def run(self):
        # Create a new event loop for the async voice listener
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Direct execution: listen and emit
            text = loop.run_until_complete(self.voice.listen())
            if self._is_active:
                self.text_received.emit(text if text else "")
        except Exception as e:
            logger.error(f"VoiceWorker Error: {e}")
            self.error_signal.emit(str(e))
        finally:
            loop.close()

    def stop(self):
        self._is_active = False

class ArvynApp(ArvynOrb):
    """
    The Core Application Controller.
    Optimized for direct command processing and Glass Morphism UI.
    """
    def __init__(self):
        super().__init__()
        self.worker = None
        self.voice = ArvynVoice()
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
        
        logger.info("Agent Arvyn UI initialized and ready for direct commands.")

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
        """Direct execution: processes user input without ID checks."""
        if self.worker and self.worker.isRunning():
            self.dashboard.append_log("Arvyn is busy. Stop the current task first.")
            return

        logger.info(f"Processing direct command: {command_text}")
        self.worker = AgentWorker(command_text)
        self.worker.log_signal.connect(self.dashboard.append_log)
        self.worker.status_signal.connect(self._update_ui_status)
        self.worker.screenshot_signal.connect(self.dashboard.update_screenshot)
        self.worker.approval_signal.connect(self._toggle_approval_ui)
        self.worker.start()

    def kill_agent(self):
        """Emergency stop logic."""
        if self.worker and self.worker.isRunning():
            logger.warning("Manual stop triggered.")
            self.worker.stop()
            self.worker.wait(1000)
            if self.worker.isRunning():
                self.worker.terminate()
            self._update_ui_status("Stopped")

    def _update_ui_status(self, status: str):
        self.dashboard.header.setText(f"ARVYN: {status.upper()}")
        self.status_label.setText(status)

    def _toggle_approval_ui(self, show: bool):
        if show:
            self.dashboard.interaction_stack.setCurrentIndex(1)
            self.activateWindow()
        else:
            self.dashboard.interaction_stack.setCurrentIndex(0)

    def trigger_voice_input(self):
        if (self.voice_worker and self.voice_worker.isRunning()):
            return
        self.dashboard.append_log("Listening...")
        self.voice_worker = VoiceWorker(self.voice)
        self.voice_worker.text_received.connect(self._handle_voice_success)
        self.voice_worker.start()

    def _handle_voice_success(self, text):
        if text:
            self.dashboard.input_field.setText(text)
            self.process_command(text)

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