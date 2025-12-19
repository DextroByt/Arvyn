import asyncio
import logging
import queue
import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal
from langgraph.checkpoint.memory import MemorySaver
from core.agent_orchestrator import ArvynOrchestrator
from config import logger

class VoiceWorker(QThread):
    """
    Advanced Manual-Stop Voice Worker.
    Records audio continuously into a buffer until the stop signal is received.
    """
    text_received = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        self._is_active = True

    def stop(self):
        """Triggers the end of the recording loop."""
        self._is_active = False

    def run(self):
        self.status_signal.emit("Listening...")
        logger.info("VoiceWorker: Microphone hot.")
        
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_chunks = []
                
                while self._is_active:
                    try:
                        # Small increments to stay responsive to the toggle
                        chunk = self.recognizer.listen(source, timeout=1, phrase_time_limit=2)
                        audio_chunks.append(chunk)
                    except sr.WaitTimeoutError:
                        continue
                
                if not audio_chunks:
                    self.text_received.emit("")
                    return

                combined_audio = sr.AudioData(
                    b"".join([c.get_raw_data() for c in audio_chunks]),
                    audio_chunks[0].sample_rate,
                    audio_chunks[0].sample_width
                )

            self.status_signal.emit("Transcribing...")
            text = self.recognizer.recognize_google(combined_audio)
            self.text_received.emit(text)
            
        except sr.UnknownValueError:
            self.text_received.emit("")
        except Exception as e:
            logger.error(f"VoiceWorker Error: {e}")
            self.text_received.emit("")

class AgentWorker(QThread):
    """
    The Global Session Worker.
    Maintains a persistent browser instance and processes commands sequentially.
    """
    log_signal = pyqtSignal(str)
    screenshot_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    approval_signal = pyqtSignal(bool)
    finished_signal = pyqtSignal(dict)

    # Shared memory to persist conversation state across commands
    _shared_checkpointer = MemorySaver()

    def __init__(self):
        super().__init__()
        self.command_queue = queue.Queue()
        self.orchestrator = None
        self.loop = None
        self._is_running = True
        self.config = {"configurable": {"thread_id": "arvyn_persistent_session"}}

    def submit_command(self, user_command: str):
        """Adds a new task to the persistent session queue."""
        self.command_queue.put(user_command)

    def stop_persistent_session(self):
        """Manually shuts down the browser and thread."""
        self._is_running = False
        if self.orchestrator and self.loop:
            asyncio.run_coroutine_threadsafe(self.orchestrator.cleanup(), self.loop)
        self.command_queue.put(None) # Sentinel to break the loop

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize the browser once and keep it open
        self.orchestrator = ArvynOrchestrator()
        self.loop.run_until_complete(self.orchestrator.init_app(self._shared_checkpointer))
        
        try:
            while self._is_running:
                # Wait for next command from the queue
                command = self.command_queue.get()
                if command is None: break 
                
                self.loop.run_until_complete(self.execute_task(command))
                self.command_queue.task_done()
        except Exception as e:
            logger.error(f"Persistent Worker Error: {e}")
        finally:
            self.loop.close()

    async def execute_task(self, user_command: str):
        """Executes a command within the existing browser session."""
        try:
            self.status_signal.emit("Thinking...")
            self.log_signal.emit(f"Processing: '{user_command}'")
            initial_input = {"messages": [("user", user_command)]}

            async for event in self.orchestrator.app.astream(initial_input, config=self.config):
                if not self._is_running: return
                for node_name, output in event.items():
                    self._handle_node_output(node_name, output)

            # Check for HITL (Human-In-The-Loop) checkpoints
            state_data = self.orchestrator.app.get_state(self.config)
            if state_data.next and "human_approval_node" in state_data.next:
                self.status_signal.emit("Awaiting Interaction")
                self.approval_signal.emit(True)
            else:
                self.status_signal.emit("Ready")
                
        except Exception as e:
            logger.error(f"Task Execution Error: {e}")
            self.log_signal.emit(f"Task Halted: {str(e)}")
            self.status_signal.emit("Error")

    def _handle_node_output(self, node_name: str, output: dict):
        if "messages" in output:
            for msg in output["messages"]:
                content = msg[1] if isinstance(msg, tuple) else getattr(msg, 'content', str(msg))
                if content.strip():
                    self.log_signal.emit(content)
        if "current_step" in output:
            self.status_signal.emit(output["current_step"])
        if "screenshot" in output and output["screenshot"]:
            self.screenshot_signal.emit(output["screenshot"])

    def resume_with_approval(self, approved: bool):
        """Resumes the graph after human interaction (e.g., login approval)."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._resume_logic(approved), self.loop)

    async def _resume_logic(self, approved: bool):
        decision = "approved" if approved else "rejected"
        await self.orchestrator.app.update_state(self.config, {"human_approval": decision})
        self.log_signal.emit(f"Interaction: {decision}. Moving to sub-task...")
        self.approval_signal.emit(False)
        
        async for event in self.orchestrator.app.astream(None, config=self.config):
            if not self._is_running: return
            for node_name, output in event.items():
                self._handle_node_output(node_name, output)
        self.status_signal.emit("Ready")