import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from gui.widget_orb import ArvynOrb
from gui.dashboard import ArvynDashboard
from gui.threads import ArvynWorker

class ArvynApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Agent Arvyn")
        
        # 1. Initialize UI Components
        self.orb = ArvynOrb()
        self.dashboard = ArvynDashboard()
        
        # 2. State Management
        self.worker = None
        
        # 3. Connect UI Interactions
        self._connect_signals()
        
        # 4. Show the Orb (Start State)
        self.orb.show()

    def _connect_signals(self):
        """Wiring the logic between the Orb, Dashboard, and Worker."""
        
        # Orb Actions
        self.orb.toggle_dashboard = self.toggle_dashboard
        
        # Dashboard Actions
        self.dashboard.input_submitted.connect(self.handle_user_input)
        self.dashboard.approval_granted.connect(self.handle_approval)

    def toggle_dashboard(self):
        """Shows or hides the dashboard when the Orb is double-clicked."""
        if self.dashboard.isVisible():
            self.dashboard.hide()
        else:
            self.dashboard.show()
            self.dashboard.raise_()
            self.dashboard.activateWindow()

    def handle_user_input(self, text: str):
        """
        Routes text from the Dashboard to the active Agent Worker.
        If no worker exists, it starts a new mission.
        """
        if self.worker and self.worker.isRunning():
            # Resume an interrupted graph (e.g., providing missing data)
            self.worker.resume_agent(text)
            self.dashboard.log(f"User Provided: {text}")
        else:
            # Start a brand new automation cycle
            self.start_new_mission(text)

    def start_new_mission(self, prompt: str):
        """Initializes the thread-safe worker for a new task."""
        self.dashboard.log(f"New Mission Started: {prompt}")
        self.worker = ArvynWorker(prompt)
        
        # Connect Worker signals to UI updates
        self.worker.signals.status_updated.connect(self.dashboard.set_status)
        self.worker.signals.input_requested.connect(self.dashboard.request_input)
        self.worker.signals.approval_required.connect(self.dashboard.request_approval)
        self.worker.signals.execution_finished.connect(self.on_mission_complete)
        self.worker.signals.error_occurred.connect(lambda e: self.dashboard.log(f"ERROR: {e}"))
        
        self.worker.start()

    def handle_approval(self, decision: str):
        """Handles the final 'Approve' signal from the Dashboard."""
        if self.worker:
            self.worker.resume_agent(decision)
            self.dashboard.reset_controls()
            self.dashboard.log("Approval received. Proceeding to finalize transaction...")

    def on_mission_complete(self, success: bool):
        """Cleanup after a mission ends."""
        status = "Mission Accomplished" if success else "Mission Failed"
        self.dashboard.set_status(status)
        self.dashboard.reset_controls()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    # Create and run the Arvyn Application
    arvyn = ArvynApp()
    arvyn.run()