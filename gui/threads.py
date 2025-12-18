import asyncio
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from qasync import asyncSlot

from core.agent_orchestrator import ArvynOrchestrator
from config import logger

class BridgeSignals(QObject):
    """
    Standardizes communication between the Async Brain and the Qt UI.
    """
    status_updated = pyqtSignal(str, str)  # (Message, Level)
    orb_state_changed = pyqtSignal(str)    # (thinking, idle, success, error)
    request_approval = pyqtSignal(str)     # (Reason)
    task_finished = pyqtSignal(bool)       # (Success/Fail)

class AsyncAgentWorker:
    """
    The Orchestrator Wrapper. 
    Runs the LangGraph agent inside the qasync event loop.
    """
    def __init__(self, signals: BridgeSignals):
        self.orchestrator = ArvynOrchestrator()
        self.signals = signals
        self._approval_event = asyncio.Event()

    async def run_task(self, user_command: str):
        """
        Starts the asynchronous agent loop and streams updates to the GUI and Console.
        """
        logger.info(f"Worker starting task: {user_command}")
        self.signals.orb_state_changed.emit("thinking")
        self.signals.status_updated.emit(f"Initializing mission: {user_command}", "INFO")

        try:
            # We stream the graph execution to provide real-time feedback in console
            async for output in self.orchestrator.run(user_command):
                for node_name, state_update in output.items():
                    logger.debug(f"Graph Transition: Node '{node_name}' completed.")
                    
                    if "ui_message" in state_update:
                        msg = state_update["ui_message"]
                        logger.info(f"[REASONING] {msg}")
                        self.signals.status_updated.emit(msg, "REASONING")
                    
                    if "error_message" in state_update and state_update["error_message"]:
                        logger.error(f"[EXECUTION FAIL] {state_update['error_message']}")
                        self.signals.status_updated.emit(state_update["error_message"], "ERROR")
                    
                    # Human-in-the-Loop Pause logic
                    if "Waiting for manual verification" in state_update.get("ui_message", ""):
                        logger.warning("Agent Paused: Awaiting User Approval in Dashboard.")
                        self.signals.orb_state_changed.emit("idle")
                        self.signals.request_approval.emit("Safety Check Required")
                        await self._approval_event.wait()
                        self._approval_event.clear()
                        logger.info("Approval Received. Resuming Graph...")
                        self.signals.orb_state_changed.emit("thinking")

            self.signals.orb_state_changed.emit("success")
            self.signals.status_updated.emit("Task complete.", "SUCCESS")
            self.signals.task_finished.emit(True)

        except Exception as e:
            logger.exception("CRITICAL: Worker Task Encountered Unhandled Exception")
            self.signals.orb_state_changed.emit("error")
            self.signals.status_updated.emit(f"Critical Error: {str(e)}", "ERROR")
            self.signals.task_finished.emit(False)

    def grant_approval(self):
        """Called by the GUI to resume the agent's execution."""
        self._approval_event.set()

    async def shutdown(self):
        """Ensures the browser and playwright processes die with the app (Fixed typo)."""
        logger.info("Cleaning up browser resources...")
        await self.orchestrator.browser.stop() # Typo 'ss' removed here