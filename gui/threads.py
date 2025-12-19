import asyncio
import logging
from PyQt6.QtCore import QThread, pyqtSignal
from langgraph.checkpoint.memory import MemorySaver
from core.agent_orchestrator import ArvynOrchestrator
from config import logger

class AgentWorker(QThread):
    """
    The bridge between the asynchronous LangGraph brain and the PyQt6 UI.
    Updated to maintain the session loop during Human-In-The-Loop interrupts.
    """
    
    log_signal = pyqtSignal(str)
    screenshot_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    approval_signal = pyqtSignal(bool)
    finished_signal = pyqtSignal(dict)

    # Persistent checkpointer to maintain context across different user commands
    _shared_checkpointer = MemorySaver()

    def __init__(self, user_command: str):
        super().__init__()
        self.user_command = user_command
        self.orchestrator = None
        self.loop = None
        self._is_running = True
        # Keep thread_id consistent for multi-turn direct execution
        self.config = {"configurable": {"thread_id": "arvyn_direct_session"}}

    def stop(self):
        """Emergency stop: flags the loop to abort immediately."""
        self._is_running = False
        logger.warning("AgentWorker: Stop requested.")

    def run(self):
        """Lifecycle manager for the background task."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            # 1. Execute the initial task (runs until completion or HITL breakpoint)
            self.loop.run_until_complete(self.execute_task())
            
            # 2. Keep the loop alive for interaction. 
            # This prevents the 'finally' block from closing the browser while waiting for approval.
            while self._is_running:
                # We check the state frequently to see if we should continue existing
                self.loop.run_until_complete(asyncio.sleep(0.5))
                
                # Optional: If the task is finished and no HITL is pending, we can exit
                if self.orchestrator:
                    state = self.orchestrator.app.get_state(self.config)
                    if not state.next and self._is_task_complete:
                        break

        except Exception as e:
            logger.error(f"Worker Thread Error: {e}")
            self.log_signal.emit(f"System Error: {str(e)}")
        finally:
            # Cleanup only happens when the loop is truly finished or stopped
            if self.orchestrator:
                logger.info("Cleaning up browser resources...")
                self.loop.run_until_complete(self.orchestrator.cleanup())
            self.loop.close()
            logger.info("AgentWorker thread finished.")

    async def execute_task(self):
        """Initializes the orchestrator and manages the initial task flow."""
        self.orchestrator = ArvynOrchestrator()
        self._is_task_complete = False
        
        try:
            await self.orchestrator.init_app(self._shared_checkpointer)
            
            self.status_signal.emit("Analyzing...")
            self.log_signal.emit(f"Command: '{self.user_command}'")

            initial_input = {"messages": [("user", self.user_command)]}

            # Stream events from the LangGraph application
            async for event in self.orchestrator.app.astream(initial_input, config=self.config):
                if not self._is_running: 
                    self.log_signal.emit("Action aborted.")
                    return
                
                for node_name, output in event.items():
                    self._handle_node_output(node_name, output)

            # Check if the graph has paused for human approval
            state_data = self.orchestrator.app.get_state(self.config)
            if state_data.next and "human_approval_node" in state_data.next:
                self.status_signal.emit("Awaiting Approval")
                self.approval_signal.emit(True)
            else:
                self._is_task_complete = True
                self.status_signal.emit("Ready")
                self.finished_signal.emit({"status": "complete"})
                
        except Exception as e:
            logger.error(f"Task Execution Error: {e}")
            self.log_signal.emit(f"Halted: {str(e)}")
            self.status_signal.emit("Error")
            self._is_task_complete = True

    def _handle_node_output(self, node_name: str, output: dict):
        """Updates the Dashboard based on real-time graph node output."""
        if "messages" in output:
            for msg in output["messages"]:
                if isinstance(msg, tuple):
                    content = msg[1]
                elif hasattr(msg, 'content'):
                    content = msg.content
                else:
                    content = str(msg)
                
                if content.strip():
                    self.log_signal.emit(content)

        if "current_step" in output:
            self.status_signal.emit(output["current_step"])

        if "screenshot" in output and output["screenshot"]:
            self.screenshot_signal.emit(output["screenshot"])

    def resume_with_approval(self, approved: bool):
        """Restarts the graph flow after a user confirms via Dashboard buttons."""
        if self.loop and self.loop.is_running():
            # Schedule the resume logic in the existing loop
            asyncio.run_coroutine_threadsafe(self._resume_logic(approved), self.loop)

    async def _resume_logic(self, approved: bool):
        decision = "approved" if approved else "rejected"
        
        # Update state to reflect user choice
        await self.orchestrator.app.update_state(self.config, {"human_approval": decision})
        self.log_signal.emit(f"Action {decision}. Proceeding...")
        self.approval_signal.emit(False)

        # Resume streaming from the breakpoint (passing None as input continues the graph)
        async for event in self.orchestrator.app.astream(None, config=self.config):
            if not self._is_running: return
            for node_name, output in event.items():
                self._handle_node_output(node_name, output)
        
        self._is_task_complete = True
        self.status_signal.emit("Ready")