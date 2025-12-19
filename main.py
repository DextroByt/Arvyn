import sys
import asyncio
import logging
from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QRect, QEasingCurve, QTimer

# Import config first for unified logging
from config import Config, logger, ORB_SIZE, DASHBOARD_SIZE

from gui.widget_orb import ArvynOrb
from gui.dashboard import ArvynDashboard
from gui.threads import AgentWorker, VoiceWorker
from tools.voice import ArvynVoice

class ArvynApp(ArvynOrb):
    """
    The Core Application Controller (Production Grade).
    Manages persistent browser sessions and the Recursive Interaction lifecycle.
    Features: Animation Engine, Auto-Mic Toggle, and persistent TTS.
    """
    def __init__(self):
        super().__init__()
        
        # --- 1. CORE TOOLS & UI INITIALIZATION ---
        self.voice = ArvynVoice()  # Voice output tool
        self._is_expanded = False
        self.container = QStackedWidget()
        
        # Orb view (Index 0)
        self.container.addWidget(self.status_label)
        
        # Dashboard view (Index 1) - Initialized BEFORE worker connections
        self.dashboard = ArvynDashboard()
        self.container.addWidget(self.dashboard)
        
        self.layout.addWidget(self.container)

        # --- 2. PERSISTENT WORKER INITIALIZATION ---
        self.worker = AgentWorker() 
        self._connect_worker_signals()
        self.worker.start()

        self.voice_worker = None
        
        # Interaction Signal Connections
        self.clicked.connect(self.initiate_expansion)
        self.dashboard.command_submitted.connect(self.process_command)
        self.dashboard.mic_clicked.connect(self.trigger_voice_input)
        self.dashboard.approval_given.connect(self.handle_hitl_approval)
        self.dashboard.minimize_requested.connect(self.initiate_shrink)
        self.dashboard.stop_requested.connect(self.kill_agent)

        # UI Window Positioning & States
        self.move_to_default_position()
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.start_pulse()
        
        logger.info("Arvyn 2.0: Interactive Core initialized and pulsing.")

    def _connect_worker_signals(self):
        """Connects the orchestrator worker to UI updates and TTS synthesis."""
        self.worker.log_signal.connect(self.dashboard.append_log)
        self.worker.status_signal.connect(self._update_ui_status)
        self.worker.screenshot_signal.connect(self.dashboard.update_screenshot)
        self.worker.approval_signal.connect(self._toggle_approval_ui)
        
        # Recursive Voice Signals for hands-free automation
        self.worker.speak_signal.connect(self.voice.speak)
        self.worker.auto_mic_signal.connect(self._handle_auto_mic_logic)

    def _handle_auto_mic_logic(self, should_start: bool):
        """
        Orchestrates the 'Speak -> Listen' transition.
        Automatically opens the mic after a delay to ensure the user hears Arvyn's question.
        """
        if should_start and not self.dashboard.is_listening:
            # 1.5s delay allows the TTS engine to begin playing before the mic opens
            QTimer.singleShot(1500, self.dashboard._toggle_mic)

    def move_to_default_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - self.width() - 40
        y = screen.height() - self.height() - 40
        self.move(x, y)

    def initiate_expansion(self):
        """Morphs the Orb into the full Dashboard with easing animations."""
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
        """Shrinks the dashboard back to a small orb."""
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
        """Submits text or transcribed voice to the executor."""
        if command_text.strip():
            self.worker.submit_command(command_text)

    def trigger_voice_input(self, should_start: bool):
        """Toggles the VoiceWorker for speech transcription."""
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
            self._update_ui_status("Ready")

    def kill_agent(self):
        """Cleanly releases browser and worker resources."""
        if self.worker and self.worker.isRunning():
            self.worker.stop_persistent_session()
            self._update_ui_status("Stopped")
            self.dashboard.append_log("Browser resources released successfully.")

    def _update_ui_status(self, status: str):
        self.dashboard.header.setText(f"ARVYN: {status.upper()}")
        self.status_label.setText(status)

    def _toggle_approval_ui(self, show: bool):
        """Switches Dashboard view to the Human-In-The-Loop approval stack."""
        self.dashboard.interaction_stack.setCurrentIndex(1 if show else 0)
        if show: self.activateWindow()

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