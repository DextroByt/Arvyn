import asyncio
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from core.agent_orchestrator import ArvynOrchestrator
from langgraph.types import Command

class AgentSignals(QObject):
    """Defines the signals available for the Agent Thread."""
    status_updated = pyqtSignal(str)       # Updates status text on Dashboard
    input_requested = pyqtSignal(str)      # Triggers a popup for missing data
    approval_required = pyqtSignal(str)    # Activates the 'Approve' button
    execution_finished = pyqtSignal(bool)  # Notifies when the cycle ends
    error_occurred = pyqtSignal(str)       # Reports errors to the UI logs

class ArvynWorker(QThread):
    def __init__(self, user_input: str):
        super().__init__()
        self.user_input = user_input
        self.signals = AgentSignals()
        self.orchestrator = ArvynOrchestrator()
        
        # Internal state to handle the "Resume" signal from the UI
        self.resume_data = None
        self._resume_event = asyncio.Event()

    def run(self):
        """Entry point for the thread; starts the async event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.execute_agent())

    async def execute_agent(self):
        """
        Runs the LangGraph workflow and handles 'interrupts'.
        """
        thread_config = {"configurable": {"thread_id": "arvyn_session_1"}}
        initial_state = {"messages": [{"role": "user", "content": self.user_input}]}

        try:
            # 1. Start the graph stream
            async for event in self.orchestrator.workflow.astream(
                initial_state, thread_config, stream_mode="values"
            ):
                # Process events and update UI status
                if "status" in event:
                    self.signals.status_updated.emit(f"Arvyn: {event['status']}...")

                # 2. Check for Interrupts (Conscious Pauses)
                snapshot = await self.orchestrator.workflow.aget_state(thread_config)
                if snapshot.next:
                    await self.handle_interrupt(snapshot)

            self.signals.execution_finished.emit(True)

        except Exception as e:
            self.signals.error_occurred.emit(str(e))
            self.signals.execution_finished.emit(False)

    async def handle_interrupt(self, snapshot):
        """Dispatches interrupts to the GUI and waits for user response."""
        interrupt_val = snapshot.tasks[0].interrupts[0].value
        
        if "INPUT_REQUESTED" in interrupt_val:
            field_name = interrupt_val.split(":")[1]
            self.signals.input_requested.emit(field_name)
        elif "FINAL_APPROVAL" in interrupt_val:
            self.signals.approval_required.emit("Please verify the payment amount.")

        # PAUSE: Wait for the main thread to call resume_agent()
        self._resume_event.clear()
        await self._resume_event.wait()

        # RESUME: Feed the user's input back into the graph
        await self.orchestrator.workflow.ainvoke(
            Command(resume=self.resume_data),
            config={"configurable": {"thread_id": "arvyn_session_1"}}
        )

    def resume_agent(self, data: str):
        """Called by the Dashboard when you click 'Submit' or 'Approve'."""
        self.resume_data = data
        self._resume_event.set()