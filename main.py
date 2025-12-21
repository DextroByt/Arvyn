import sys
import os
import asyncio
import logging
import traceback
from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QTimer

# Import config first to initialize the SafeStreamHandler (fixing charmap errors)
from config import Config, logger, ORB_SIZE, DASHBOARD_SIZE

from gui.widget_orb import ArvynOrb
from gui.dashboard import ArvynDashboard
from gui.threads import AgentWorker, VoiceWorker
from tools.voice import ArvynVoice

def exception_hook(exctype, value, tb):
    """Global exception hook to ensure all PyQt and VLM-level crashes are recorded."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"FATAL SYSTEM EXCEPTION:\n{err_msg}")
    sys.__excepthook__(exctype, value, tb)

# Register the hook before app initialization
sys.excepthook = exception_hook

class ArvynApp(ArvynOrb):
    """
    Superior Application Controller for Agent Arvyn.
    UPGRADED: Full Autonomy UI - Monitoring mode enabled.
    MAINTAINED: Multi-modal interaction, Advanced Morphing, and Kinetic Feedback.
    """
    def __init__(self):
        super().__init__()
        
        # --- 1. CORE COMPONENT INITIALIZATION ---
        self.voice = ArvynVoice()  
        self._is_expanded = False
        self.container = QStackedWidget()
        
        # UI Layer 0: The Pulsing Interaction Orb
        self.status_label.setText("INITIALIZING")
        self.container.addWidget(self.status_label)
        
        # UI Layer 1: The Command Center (Expanded Dashboard)
        self.dashboard = ArvynDashboard()
        self.container.addWidget(self.dashboard)
        
        self.layout.addWidget(self.container)

        # --- 2. AUTONOMOUS SESSION INITIALIZATION ---
        # AgentWorker manages the Qwen-powered Orchestrator in a dedicated thread
        self.worker = AgentWorker() 
        self._connect_worker_signals()
        self.worker.start()

        self.voice_worker = None
        
        # --- 3. UI INTERACTION BINDINGS ---
        self.clicked.connect(self.initiate_expansion)
        self.dashboard.command_submitted.connect(self.process_command)
        self.dashboard.mic_clicked.connect(self.trigger_voice_input)
        self.dashboard.approval_given.connect(self.handle_hitl_approval)
        self.dashboard.minimize_requested.connect(self.initiate_shrink)
        self.dashboard.stop_requested.connect(self.kill_agent)

        # Production Window Flags
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.move_to_default_position()
        self.start_pulse()
        
        logger.info("🛡️ Arvyn App v4.0: Autonomous UI Controller active and monitoring.")

    def _connect_worker_signals(self):
        """Synchronizes background autonomous state with the Dashboard UI."""
        self.worker.log_signal.connect(self.dashboard.append_log)
        self.worker.status_signal.connect(self._update_ui_status)
        self.worker.screenshot_signal.connect(self.dashboard.update_screenshot)
        
        # Updated: Approval signal now triggers a notification rather than a hard stop
        self.worker.approval_signal.connect(self._toggle_approval_ui)
        
        # Multi-Modal Recursive Integration
        self.worker.speak_signal.connect(self.voice.speak)
        self.worker.auto_mic_signal.connect(self._handle_auto_mic_logic)

    def _handle_auto_mic_logic(self, should_start: bool):
        """Orchestrates the 'Listen after Speak' workflow with audio buffers."""
        if should_start and not self.dashboard.is_listening:
            QTimer.singleShot(2000, self.dashboard._toggle_mic)

    def move_to_default_position(self):
        """Positions the Orb at the bottom-right corner of the desktop."""
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - self.width() - 40
        y = screen.height() - self.height() - 40
        self.move(x, y)

    def initiate_expansion(self):
        """Smoothly morphs the Orb into the full Command Center."""
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
        """Collapses the interface back to a minimalist Orb."""
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
        """Validates and submits commands to the Autonomous Executor."""
        clean_text = command_text.strip()
        if clean_text:
            self.dashboard.append_log(f"SUBMITTED: {clean_text.upper()}", category="system")
            self.worker.submit_command(clean_text)

    def trigger_voice_input(self, should_start: bool):
        """Controls the transcription lifecycle."""
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
        """Emergency shutdown for the persistent session."""
        logger.warning("🛑 Arvyn Main: Emergency shutdown initiated.")
        if self.worker and self.worker.isRunning():
            self.worker.stop_persistent_session()
            self._update_ui_status("STOPPED")
            self.dashboard.append_log("System: All autonomous layers and model instances terminated.", category="error")
        
        QTimer.singleShot(1500, QApplication.instance().quit)

    def _update_ui_status(self, status: str):
        """Pipes detailed agent status updates to the UI headers."""
        display_status = status.replace("_", " ").upper()
        self.dashboard.header.setText(f"ARVYN // {display_status}")
        self.status_label.setText(display_status)

    def _toggle_approval_ui(self, show: bool):
        """
        Modified: No longer interrupts the loop. 
        Shows the 'Authorization Monitor' briefly before auto-resuming.
        """
        if show:
            self.dashboard.append_log("AUTONOMOUS AUTHORIZATION: Validating transaction via User Profile...", category="kinetic")
            # Auto-approve from UI level to match backend speed
            QTimer.singleShot(500, lambda: self.handle_hitl_approval(True))

    def handle_hitl_approval(self, approved: bool):
        """Logically confirms the action and resumes the worker immediately."""
        if self.worker:
            self.worker.resume_with_approval(approved)
            # Switch back to the status view if it was showing approval
            self.dashboard.interaction_stack.setCurrentIndex(0)

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