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
    Optimized for streaming audio chunks and high-accuracy transcription 
    during interactive banking sessions.
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
                # Dynamic calibration for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                audio_chunks = []
                
                while self._is_active:
                    try:
                        # Short listening windows to remain responsive to the 'Stop' toggle
                        chunk = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                        audio_chunks.append(chunk)
                    except sr.WaitTimeoutError:
                        continue
                
                if not audio_chunks:
                    self.text_received.emit("")
                    return

                # Compile chunks into a single audio object for transcription
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
    Maintains a persistent browser and manages the recursive 'Auto-Mic' lifecycle.
    Updated with Defensive State Management to prevent 'intent' key errors.
    """
    log_signal = pyqtSignal(str)
    screenshot_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    approval_signal = pyqtSignal(bool)
    
    # Signals for the Interactive Voice Loop
    speak_signal = pyqtSignal(str)      # Triggers TTS in main app
    auto_mic_signal = pyqtSignal(bool)  # Automatically toggles the mic button
    
    finished_signal = pyqtSignal(dict)

    # Persistent state storage across multiple commands
    _shared_checkpointer = MemorySaver()

    def __init__(self):
        super().__init__()
        self.command_queue = queue.Queue()
        self.orchestrator = None
        self.loop = None
        self._is_running = True
        # Thread ID for session continuity in banking tasks
        self.config = {"configurable": {"thread_id": "arvyn_banking_session_v3"}}

    def submit_command(self, user_command: str):
        """Adds a new task (Voice or Text) to the processing queue."""
        self.command_queue.put(user_command)

    def stop_persistent_session(self):
        """Clean shutdown of browser and internal event loops."""
        self._is_running = False
        if self.orchestrator and self.loop:
            asyncio.run_coroutine_threadsafe(self.orchestrator.cleanup(), self.loop)
        self.command_queue.put(None)

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Start the persistent browser session
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
            self.loop.close()

    async def execute_task(self, user_command: str):
        """Processes a command through the recursive autonomous banking loop."""
        try:
            self.status_signal.emit("Thinking...")
            self.log_signal.emit(f"User Request: {user_command}")
            
            # Resume or start the state graph
            initial_input = {"messages": [("user", user_command)]}

            if not self.orchestrator.app:
                raise Exception("Orchestrator App not properly initialized.")

            async for event in self.orchestrator.app.astream(initial_input, config=self.config):
                if not self._is_running: return
                for node_name, output in event.items():
                    self._handle_node_output(node_name, output)

            # --- POST-ACTION REASONING: Check if we need user input ---
            state_data = self.orchestrator.app.get_state(self.config)
            
            # Defensive access to avoid KeyError if state is sparse
            values = state_data.values or {}
            next_nodes = state_data.next or []

            if "human_interaction_node" in next_nodes:
                question = values.get("pending_question")
                if question:
                    self.status_signal.emit("Questioning...")
                    self.speak_signal.emit(question)
                    # Signal main.py to activate the mic after speech synthesis
                    self.auto_mic_signal.emit(True) 
                
                self.approval_signal.emit(True) # Fallback to manual buttons
            else:
                self.status_signal.emit("Ready")
                
        except Exception as e:
            logger.error(f"Task Execution Error: {e}")
            self.log_signal.emit(f"Internal System Error: {str(e)}")
            self.status_signal.emit("Error")

    def _handle_node_output(self, node_name: str, output: dict):
        """Streams updates to the Dashboard UI with safety checks."""
        if not output: return

        if "messages" in output:
            for msg in output["messages"]:
                content = msg[1] if isinstance(msg, tuple) else getattr(msg, 'content', str(msg))
                if content.strip():
                    self.log_signal.emit(content)
        
        if "current_step" in output:
            self.status_signal.emit(output["current_step"])
            self.log_signal.emit(f"Status: {output['current_step']}")
            
        if "screenshot" in output and output["screenshot"]:
            self.screenshot_signal.emit(output["screenshot"])

    def resume_with_approval(self, approved: bool):
        """Resumes the graph after manual human interaction."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._resume_logic(approved), self.loop)

    async def _resume_logic(self, approved: bool):
        decision = "approved" if approved else "rejected"
        # Update the state with the human decision
        await self.orchestrator.app.update_state(self.config, {"human_approval": decision})
        self.log_signal.emit(f"Manual Override: {decision}")
        self.approval_signal.emit(False)
        
        # Continue streaming from the point of interruption
        async for event in self.orchestrator.app.astream(None, config=self.config):
            if not self._is_running: return
            for node_name, output in event.items():
                self._handle_node_output(node_name, output)
        self.status_signal.emit("Ready")