import asyncio
import logging
import queue
import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from langgraph.checkpoint.memory import MemorySaver
from core.agent_orchestrator import ArvynOrchestrator
from config import logger

class VoiceWorker(QThread):
    """
    Advanced Manual-Stop Voice Worker.
    Optimized for streaming audio chunks and high-accuracy transcription.
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
        logger.info("VoiceWorker: Microphone engaged for user response.")
        
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                audio_chunks = []
                
                while self._is_active:
                    try:
                        chunk = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
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
            logger.info(f"STT Result: {text}")
            self.text_received.emit(text)
            
        except sr.UnknownValueError:
            logger.warning("VoiceWorker: Could not understand audio.")
            self.text_received.emit("")
        except Exception as e:
            logger.error(f"VoiceWorker Critical Error: {e}")
            self.text_received.emit("")

class AgentWorker(QThread):
    """
    The Global Session Orchestration Worker.
    Fixed: Proper event loop management and awaited cleanup to prevent RuntimeWarnings.
    """
    log_signal = pyqtSignal(str)
    screenshot_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    approval_signal = pyqtSignal(bool)
    speak_signal = pyqtSignal(str)
    auto_mic_signal = pyqtSignal(bool)
    finished_signal = pyqtSignal(dict)

    _shared_checkpointer = MemorySaver()

    def __init__(self):
        super().__init__()
        self.command_queue = queue.Queue()
        self.orchestrator = None
        self.loop = None
        self._is_running = True
        self.config = {"configurable": {"thread_id": "arvyn_banking_session_v4"}}

    def submit_command(self, user_command: str):
        self.command_queue.put(user_command)

    def stop_persistent_session(self):
        """Clean shutdown of browser and internal event loops."""
        self._is_running = False
        if self.orchestrator and self.loop and self.loop.is_running():
            # Schedule the awaited cleanup in the worker's event loop
            asyncio.run_coroutine_threadsafe(self.orchestrator.cleanup(), self.loop)
        self.command_queue.put(None)

    def run(self):
        """Initializes the event loop and manages the task processing cycle."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.orchestrator = ArvynOrchestrator()
        self.loop.run_until_complete(self.orchestrator.init_app(self._shared_checkpointer))
        
        try:
            while self._is_running:
                command = self.command_queue.get()
                if command is None: break 
                
                self.loop.run_until_complete(self.execute_task(command))
                self.command_queue.task_done()
        except Exception as e:
            logger.error(f"AgentWorker Runtime Error: {e}")
        finally:
            # Ensure the loop handles the cleanup coroutine before closing
            pending = asyncio.all_tasks(self.loop)
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending))
            self.loop.close()
            logger.info("AgentWorker: Event loop closed safely.")

    async def execute_task(self, user_command: str):
        """Processes a command through the recursive autonomous banking loop."""
        try:
            self.status_signal.emit("Thinking...")
            self.log_signal.emit(f"User Request: {user_command}")
            
            initial_input = {"messages": [("user", user_command)]}

            if not self.orchestrator.app:
                raise Exception("Orchestrator App not properly initialized.")

            async for event in self.orchestrator.app.astream(initial_input, config=self.config):
                if not self._is_running: return
                for node_name, output in event.items():
                    self._handle_node_output(node_name, output)

            state_data = self.orchestrator.app.get_state(self.config)
            values = state_data.values or {}
            next_nodes = state_data.next or []

            if "human_interaction_node" in next_nodes:
                question = values.get("pending_question")
                if question:
                    self.status_signal.emit("Questioning...")
                    self.speak_signal.emit(question)
                    self.auto_mic_signal.emit(True) 
                self.approval_signal.emit(True)
            else:
                self.status_signal.emit("Ready")
                
        except Exception as e:
            logger.error(f"Task Execution Error: {e}")
            self.log_signal.emit(f"Internal System Error: {str(e)}")
            self.status_signal.emit("Error")

    def _handle_node_output(self, node_name: str, output: dict):
        if not output: return

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
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._resume_logic(approved), self.loop)

    async def _resume_logic(self, approved: bool):
        decision = "approved" if approved else "rejected"
        await self.orchestrator.app.update_state(self.config, {"human_approval": decision})
        self.log_signal.emit(f"Manual Override: {decision}")
        self.approval_signal.emit(False)
        
        async for event in self.orchestrator.app.astream(None, config=self.config):
            if not self._is_running: return
            for node_name, output in event.items():
                self._handle_node_output(node_name, output)
        self.status_signal.emit("Ready")