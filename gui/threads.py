import asyncio
import logging
import queue
import time
import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal
from langgraph.checkpoint.memory import MemorySaver
from core.agent_orchestrator import ArvynOrchestrator
from config import logger

class VoiceWorker(QThread):
    """
    Superior Voice Interaction Layer.
    Features: Adaptive ambient noise calibration, chunk-based streaming, 
    and high-accuracy Google Web Speech integration.
    """
    text_received = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        self._is_active = True
        
        # Optimize for banking environments (often has background noise)
        self.recognizer.energy_threshold = 300 
        self.recognizer.dynamic_energy_threshold = True

    def stop(self):
        """Signals the recording loop to terminate and begin transcription."""
        self._is_active = False

    def run(self):
        self.status_signal.emit("LISTENING")
        logger.info("🎙️ VoiceWorker: Microphone active.")
        
        try:
            with self.mic as source:
                # 0.8s calibration for superior noise cancellation
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                audio_chunks = []
                
                while self._is_active:
                    try:
                        # Listen in small bursts to allow for manual 'Stop' interruption
                        chunk = self.recognizer.listen(source, timeout=1, phrase_time_limit=4)
                        audio_chunks.append(chunk)
                    except sr.WaitTimeoutError:
                        continue
                
                if not audio_chunks:
                    self.text_received.emit("")
                    return

                # Compile chunks into a single audio object for the STT Engine
                combined_audio = sr.AudioData(
                    b"".join([c.get_raw_data() for c in audio_chunks]),
                    audio_chunks[0].sample_rate,
                    audio_chunks[0].sample_width
                )

            self.status_signal.emit("ANALYZING VOICE")
            text = self.recognizer.recognize_google(combined_audio)
            
            if text:
                logger.info(f"🗣️ Transcribed: {text}")
                self.text_received.emit(text)
            else:
                self.text_received.emit("")
                
        except sr.UnknownValueError:
            logger.warning("VoiceWorker: Audio unintelligible.")
            self.status_signal.emit("RETRY SPEAKING")
            self.text_received.emit("")
        except Exception as e:
            logger.error(f"VoiceWorker Critical Error: {e}")
            self.text_received.emit("")

class AgentWorker(QThread):
    """
    Superior Session Orchestration Worker.
    UPGRADED: Intelligent Task Resumption, Confidentiality-Aware Voice, 
    and hardened Async State Management.
    """
    log_signal = pyqtSignal(str)
    screenshot_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    approval_signal = pyqtSignal(bool)
    speak_signal = pyqtSignal(str)
    auto_mic_signal = pyqtSignal(bool)
    finished_signal = pyqtSignal(dict)

    # Persistence layer for multi-turn banking sessions
    _shared_checkpointer = MemorySaver()

    def __init__(self):
        super().__init__()
        self.command_queue = queue.Queue()
        self.orchestrator = None
        self.loop = None
        self._is_running = True
        
        # Consistent session ID to maintain history across turns
        self.session_config = {"configurable": {"thread_id": "arvyn_banking_prod_v3"}}

    def submit_command(self, user_command: str):
        """Thread-safe command submission."""
        self.command_queue.put(user_command)

    def stop_persistent_session(self):
        """Forces a graceful cleanup of browser and worker threads."""
        self._is_running = False
        if self.orchestrator and self.loop:
            asyncio.run_coroutine_threadsafe(self.orchestrator.cleanup(), self.loop)
        self.command_queue.put(None)

    def run(self):
        """Initializes the background async environment for Arvyn's Brain."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.orchestrator = ArvynOrchestrator()
        self.loop.run_until_complete(self.orchestrator.init_app(self._shared_checkpointer))
        
        try:
            while self._is_running:
                command = self.command_queue.get()
                if command is None: break 
                
                # Execute/Resume the LangGraph workflow
                self.loop.run_until_complete(self.execute_task(command))
                self.command_queue.task_done()
        except Exception as e:
            logger.error(f"AgentWorker Main Loop Error: {e}")
        finally:
            self._shutdown_loop()

    def _shutdown_loop(self):
        """Ensures all pending browser/api tasks are finished before thread exit."""
        try:
            pending = asyncio.all_tasks(self.loop)
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending))
            self.loop.close()
            logger.info("✅ AgentWorker: Async loop closed safely.")
        except Exception as e:
            logger.error(f"Loop Shutdown Error: {e}")

    async def execute_task(self, user_command: str):
        """
        Intelligent Task Routing.
        UPGRADED: Fixes 'A new task got created' by resuming the existing session
        if the agent is currently interrupted/paused for user input.
        """
        try:
            # Check current state to see if we are in an interrupt
            state_data = self.orchestrator.app.get_state(self.session_config)
            next_nodes = state_data.next or []

            if "human_interaction_node" in next_nodes:
                self.log_signal.emit(f"Continuing current task with: {user_command}")
                # Update state with the user response and set approval to proceed
                await self.orchestrator.app.update_state(
                    self.session_config, 
                    {"messages": [("user", user_command)], "human_approval": "approved"}
                )
                
                # Resume execution from the current point
                async for event in self.orchestrator.app.astream(None, config=self.session_config):
                    if not self._is_running: return
                    for node_name, output in event.items():
                        self._sync_orchestrator_logs()
                        self._handle_node_output(node_name, output)
            else:
                # Normal New Task Entry
                self.status_signal.emit("THINKING")
                self.log_signal.emit(f"--- NEW TASK: {user_command.upper()} ---")
                
                initial_input = {"messages": [("user", user_command)]}

                # Start streaming the graph
                async for event in self.orchestrator.app.astream(initial_input, config=self.session_config):
                    if not self._is_running: return
                    for node_name, output in event.items():
                        self._sync_orchestrator_logs()
                        self._handle_node_output(node_name, output)

            # Final check to see if we hit a NEW interaction node
            self._check_for_interaction()
                
        except Exception as e:
            logger.error(f"AgentWorker Execution Error: {e}")
            self.log_signal.emit(f"⚠️ SYSTEM ERROR: {str(e)}")
            self.status_signal.emit("ERROR")

    def _check_for_interaction(self):
        """
        Hardened Interaction Logic.
        UPGRADED: Suppresses Mic for confidential data (passwords/PINs) as requested.
        """
        state_data = self.orchestrator.app.get_state(self.session_config)
        values = state_data.values or {}
        next_nodes = state_data.next or []

        if "human_interaction_node" in next_nodes:
            question = values.get("pending_question")
            if question:
                self.status_signal.emit("AWAITING USER")
                self.speak_signal.emit(question)
                
                # CONFIDENTIALITY PROTECTION: Detect password/PIN prompts
                sensitive_keys = ["password", "pin", "credential", "otp", "code"]
                is_confidential = any(k in question.lower() for k in sensitive_keys)
                
                if not is_confidential:
                    # Only auto-trigger mic for non-confidential queries
                    self.auto_mic_signal.emit(True) 
                else:
                    self.log_signal.emit("🔒 CONFIDENTIAL STEP: Mic disabled. Use buttons to Authorize.")
            
            self.approval_signal.emit(True)
        else:
            self.status_signal.emit("READY")

    def _sync_orchestrator_logs(self):
        """Pipes the high-fidelity Orchestrator session logs to the Dashboard."""
        if hasattr(self.orchestrator, 'session_log'):
            while self.orchestrator.session_log:
                log_entry = self.orchestrator.session_log.pop(0)
                self.log_signal.emit(log_entry)

    def _handle_node_output(self, node_name: str, output: dict):
        """Processes outputs from the graph for real-time visual feedback."""
        if not output: return
        if "screenshot" in output and output["screenshot"]:
            self.screenshot_signal.emit(output["screenshot"])
        if "current_step" in output:
            self.status_signal.emit(output["current_step"].upper())

    def resume_with_approval(self, approved: bool):
        """Manual trigger from the Dashboard buttons."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._resume_logic(approved), self.loop)

    async def _resume_logic(self, approved: bool):
        """Logic for manual Authorize/Reject button presses."""
        decision = "approved" if approved else "rejected"
        
        # Inject the human decision into the graph state
        await self.orchestrator.app.update_state(self.session_config, {"human_approval": decision})
        
        self.log_signal.emit(f"🛡️ USER DECISION: {decision.upper()}")
        self.approval_signal.emit(False)
        
        # Resume the graph stream from the interruption point
        async for event in self.orchestrator.app.astream(None, config=self.session_config):
            if not self._is_running: return
            for node_name, output in event.items():
                self._sync_orchestrator_logs()
                self._handle_node_output(node_name, output)
        
        # Re-check for nested or sequential interactions
        self._check_for_interaction()