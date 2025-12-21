import sys
import os
import asyncio
import logging
import traceback
from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QTimer

# Import config first to initialize the SafeStreamHandler (fixing charmap errors)
from config import (
    Config, 
    logger, 
    ORB_SIZE, 
    DASHBOARD_SIZE, 
    STRICT_AUTONOMY_MODE, 
    AUTO_APPROVAL,
    QWEN_MODEL_NAME
)

from gui.widget_orb import ArvynOrb
from gui.dashboard import ArvynDashboard
from gui.threads import AgentWorker, VoiceWorker
from tools.voice import ArvynVoice

def exception_hook(exctype, value, tb):
    """Global exception hook to ensure all PyQt-level crashes are recorded in the logs."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"FATAL UI EXCEPTION:\n{err_msg}")
    sys.__excepthook__(exctype, value, tb)

# Register the hook before app initialization
sys.excepthook = exception_hook

class ArvynApp(ArvynOrb):
    """
    Superior Application Controller for Agent Arvyn.
    UPGRADED: Features Qwen-VL Autonomous Logic (v4.5).
    FIXED: Prevents dummy-site redirects by enforcing verified site priority.
    IMPROVED: Multi-modal synchronization for un-interrupted background execution.
    """
    def __init__(self):
        super().__init__()
        
        # --- 1. CORE COMPONENT INITIALIZATION ---
        self.voice = ArvynVoice()  # Advanced TTS Output
        self._is_expanded = False
        self.container = QStackedWidget()
        
        # UI Layer 0: The Pulsing Interaction Orb
        self.container.addWidget(self.status_label)
        
        # UI Layer 1: The Command Center (Expanded Dashboard)
        # Initialized early to bind signals before the worker starts
        self.dashboard = ArvynDashboard()
        self.container.addWidget(self.dashboard)
        
        self.layout.addWidget(self.container)

        # --- 2. AUTONOMOUS SESSION INITIALIZATION ---
        # The AgentWorker manages the LangGraph/Playwright session.
        # IMPROVEMENT: Worker is now running the Qwen-VL precision engine.
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
        
        # INITIALIZATION LOG: Confirming Autonomous Status & Engine
        mode_label = "AUTONOMOUS" if STRICT_AUTONOMY_MODE else "HITL-STANDARD"
        logger.info(f"🛡️ Arvyn App v4.5: {mode_label} Controller ({QWEN_MODEL_NAME}) active.")
        self.dashboard.append_log(f"SYSTEM: Initialized with Qwen-VL Engine.", category="system")
        self.dashboard.append_log(f"MODE: {mode_label} (Zero-Auth active).", category="system")

    def _connect_worker_signals(self):
        """Synchronizes background autonomous state with the Dashboard UI."""
        self.worker.log_signal.connect(self.dashboard.append_log)
        self.worker.status_signal.connect(self._update_ui_status)
        self.worker.screenshot_signal.connect(self.dashboard.update_screenshot)
        self.worker.approval_signal.connect(self._toggle_approval_ui)
        
        # Multi-Modal Recursive Integration
        self.worker.speak_signal.connect(self.voice.speak)
        self.worker.auto_mic_signal.connect(self._handle_auto_mic_logic)

    def _handle_auto_mic_logic(self, should_start: bool):
        """
        Orchestrates the 'Listen after Speak' workflow.
        Adds a 2.0s buffer for the TTS audio to start before activating the mic.
        """
        if should_start and not self.dashboard.is_listening:
            # Buffer ensures Arvyn doesn't 'hear' its own voice
            QTimer.singleShot(2000, self.dashboard._toggle_mic)

    def move_to_default_position(self):
        """Positions the Orb at the bottom-right corner of the desktop."""
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - self.width() - 40
        y = screen.height() - self.height() - 40
        self.move(x, y)

    def initiate_expansion(self):
        """Smoothly morphs the Orb into the full Command Center using OutCubic easing."""
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
            self.dashboard.append_log(f"MANUAL INPUT: {clean_text.upper()}", category="system")
            # Clear input after submission for better UX
            self.dashboard.input_field.clear()
            self.worker.submit_command(clean_text)

    def trigger_voice_input(self, should_start: bool):
        """Controls the lifecycle of the VoiceWorker transcription thread."""
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
        """Processes transcribed text from the Voice Layer."""
        if text:
            self.dashboard.input_field.setText(text)
            self.process_command(text)
        else:
            self._update_ui_status("Ready")

    def kill_agent(self):
        """Cleanly terminates the persistent session and browser resources."""
        logger.warning("🛑 Arvyn Main: Emergency shutdown initiated.")
        if self.worker and self.worker.isRunning():
            self.worker.stop_persistent_session()
            self._update_ui_status("STOPPED")
            self.dashboard.append_log("System: All background workers and browser layers closed.", category="error")
        
        # Buffer to allow threads to close properly
        QTimer.singleShot(1500, QApplication.instance().quit)

    def _update_ui_status(self, status: str):
        """Pipes agent status updates to both Orb and Dashboard headers."""
        display_status = status.replace("_", " ").upper()
        self.dashboard.header.setText(f"ARVYN // {display_status}")
        self.status_label.setText(display_status)

    def _toggle_approval_ui(self, show: bool):
        """
        Triggers the Human-In-The-Loop UI for transaction confirmation.
        IMPROVED: If AUTO_APPROVAL is on, this logic is bypassed to maintain autonomy.
        """
        if AUTO_APPROVAL and show:
            logger.info("[MAIN] Authorization requested but AUTO-APPROVED by config.")
            self.handle_hitl_approval(True)
            return

        self.dashboard.interaction_stack.setCurrentIndex(1 if show else 0)
        if show:
            self.activateWindow()
            self.dashboard.append_log("NOTIFICATION: Sensitive field detected. Processing autonomously...", category="kinetic")

    def handle_hitl_approval(self, approved: bool):
        """Routes human approval/rejection back to the LangGraph executor."""
        if self.worker:
            self.worker.resume_with_approval(approved)

if __name__ == "__main__":
    # Prevent scaling distortions on various high-DPI displays
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    try:
        arvyn = ArvynApp()
        arvyn.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Arvyn Core Fatal Error: {e}")
        sys.exit(1)