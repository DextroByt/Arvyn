import asyncio
import logging
import io
import wave
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
                
                # We use a non-blocking listening strategy to respond to the manual stop
                # By using a phrase_time_limit and a loop, we can check our _is_active flag
                audio_chunks = []
                
                # Capture audio while the user has the mic 'Green'
                while self._is_active:
                    try:
                        # Listen in very small increments to stay responsive to the toggle
                        chunk = self.recognizer.listen(source, timeout=1, phrase_time_limit=2)
                        audio_chunks.append(chunk)
                    except sr.WaitTimeoutError:
                        continue
                
                if not audio_chunks:
                    self.text_received.emit("")
                    return

                # Combine chunks for transcription
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
    The bridge between the asynchronous LangGraph brain and the PyQt6 UI.
    Updated to keep sessions alive during the multi-stage search process.
    """
    log_signal = pyqtSignal(str)
    screenshot_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    approval_signal = pyqtSignal(bool)
    finished_signal = pyqtSignal(dict)

    _shared_checkpointer = MemorySaver()

    def __init__(self, user_command: str):
        super().__init__()
        self.user_command = user_command
        self.orchestrator = None
        self.loop = None
        self._is_running = True
        self.config = {"configurable": {"thread_id": "arvyn_direct_session"}}

    def stop(self):
        self._is_running = False
        logger.warning("AgentWorker: Stop requested.")

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.execute_task())
        except Exception as e:
            logger.error(f"Worker Thread Error: {e}")
            self.log_signal.emit(f"System Error: {str(e)}")
        finally:
            if self.orchestrator:
                self.loop.run_until_complete(self.orchestrator.cleanup())
            self.loop.close()

    async def execute_task(self):
        self.orchestrator = ArvynOrchestrator()
        try:
            await self.orchestrator.init_app(self._shared_checkpointer)
            self.status_signal.emit("Thinking...")
            self.log_signal.emit(f"Command: '{self.user_command}'")
            initial_input = {"messages": [("user", self.user_command)]}

            async for event in self.orchestrator.app.astream(initial_input, config=self.config):
                if not self._is_running: return
                for node_name, output in event.items():
                    self._handle_node_output(node_name, output)

            state_data = self.orchestrator.app.get_state(self.config)
            final_state = await state_data if asyncio.iscoroutine(state_data) else state_data
            
            if final_state.next and "human_approval_node" in final_state.next:
                self.status_signal.emit("Awaiting Approval")
                self.approval_signal.emit(True)
            else:
                self.status_signal.emit("Ready")
                self.finished_signal.emit({"status": "complete"})
        except Exception as e:
            logger.error(f"Task Execution Error: {e}")
            self.log_signal.emit(f"Halted: {str(e)}")
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
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._resume_logic(approved), self.loop)

    async def _resume_logic(self, approved: bool):
        decision = "approved" if approved else "rejected"
        await self.orchestrator.app.update_state(self.config, {"human_approval": decision})
        self.log_signal.emit(f"Action {decision}. Proceeding...")
        self.approval_signal.emit(False)
        async for event in self.orchestrator.app.astream(None, config=self.config):
            if not self._is_running: return
            for node_name, output in event.items():
                self._handle_node_output(node_name, output)
        self.status_signal.emit("Ready")