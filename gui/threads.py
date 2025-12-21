import asyncio
import logging
import queue
import time
import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal
from langgraph.checkpoint.memory import MemorySaver
from core.agent_orchestrator import ArvynOrchestrator
from config import logger, STRICT_AUTONOMY_MODE, AUTO_APPROVAL

class VoiceWorker(QThread):
    """
    Superior Voice Interaction Layer.
    UPGRADED: Enhanced for Qwen-VL Multi-modal synchronization.
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
        
        # Optimize for banking and noisy local environments
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
    UPGRADED: Qwen-VL Zero-Auth Autonomous Execution Engine.
    FIXED: Resumes without blocking for sensitive data/PIN entry.
    IMPROVED: Hardened logic for multi-site verified navigation with memory persistence.
    """
    log_signal = pyqtSignal(str)
    screenshot_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    approval_signal = pyqtSignal(bool)
    speak_signal = pyqtSignal(str)
    auto_mic_signal = pyqtSignal(bool)
    finished_signal = pyqtSignal(dict)

    # Persistence layer for multi-turn autonomous sessions (Preserved feature)
    _shared_checkpointer = MemorySaver()

    def __init__(self):
        super().__init__()
        self.command_queue = queue.Queue()
        self.orchestrator = None
        self.loop = None
        self._is_running = True
        
        # Consistent session ID to maintain history across turns with Qwen engine
        self.session_config = {"configurable": {"thread_id": "arvyn_autonomous_v4_qwen"}}

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
        """Initializes the background async environment for Arvyn's Qwen Brain."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Orchestrator now uses QwenBrain internally
        self.orchestrator = ArvynOrchestrator()
        
        # Initialize app (with Zero-Auth compilation in Orchestrator)
        self.loop.run_until_complete(self.orchestrator.init_app(self._shared_checkpointer))
        
        try:
            while self._is_running:
                command = self.command_queue.get()
                if command is None: break 
                
                # Execute/Resume the LangGraph workflow with memory support
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
            logger.info("✅ AgentWorker: Qwen-Engine session closed safely.")
        except Exception as e:
            logger.error(f"Loop Shutdown Error: {e}")

    async def execute_task(self, user_command: str):
        """
        Intelligent Autonomous Task Routing with Qwen-VL.
        IMPROVED: Handles Zero-Auth flow and automatic profile data injection.
        """
        try:
            # Check current state for potential interruptions
            state_data = self.orchestrator.app.get_state(self.session_config)
            next_nodes = state_data.next or []

            # Logic for Resuming a task (Stuck mode / Manual correction)
            if "human_interaction_node" in next_nodes:
                self.log_signal.emit(f"RESUMING TASK: {user_command}")
                await self.orchestrator.app.update_state(
                    self.session_config, 
                    {"messages": [("user", user_command)], "human_approval": "approved"}
                )
                
                async for event in self.orchestrator.app.astream(None, config=self.session_config):
                    if not self._is_running: return
                    for node_name, output in event.items():
                        self._sync_orchestrator_logs()
                        self._handle_node_output(node_name, output)
            else:
                # New Autonomous Task Entry
                self.status_signal.emit("ANALYZING")
                self.log_signal.emit(f"--- QWEN-VL AUTONOMOUS TASK: {user_command.upper()} ---")
                
                initial_input = {"messages": [("user", user_command)]}

                # Stream the graph logic
                async for event in self.orchestrator.app.astream(initial_input, config=self.session_config):
                    if not self._is_running: return
                    for node_name, output in event.items():
                        self._sync_orchestrator_logs()
                        self._handle_node_output(node_name, output)

            # Post-execution state check
            self._check_for_interaction()
                
        except Exception as e:
            logger.error(f"AgentWorker Execution Error: {e}")
            self.log_signal.emit(f"⚠️ SYSTEM ERROR: {str(e)}")
            self.status_signal.emit("ERROR")

    def _check_for_interaction(self):
        """
        Hardened Autonomous Logic check.
        FIXED: Silently handles security fields; only triggers signals if truly stuck.
        """
        state_data = self.orchestrator.app.get_state(self.session_config)
        values = state_data.values or {}
        next_nodes = state_data.next or []

        if "human_interaction_node" in next_nodes:
            question = values.get("pending_question")
            if question:
                self.status_signal.emit("NEED HELP")
                self.speak_signal.emit(question)
                self.auto_mic_signal.emit(True) 
            
            self.approval_signal.emit(True)
        else:
            analysis = values.get("browser_context", {})
            if analysis.get("action_type") == "FINISHED":
                self.status_signal.emit("COMPLETED")
                voice_prompt = analysis.get("voice_prompt")
                if voice_prompt:
                    self.speak_signal.emit(voice_prompt)
            else:
                self.status_signal.emit("READY")

    def _sync_orchestrator_logs(self):
        """Pipes High-Fidelity Orchestrator logs to the UI."""
        if hasattr(self.orchestrator, 'session_log'):
            while self.orchestrator.session_log:
                log_entry = self.orchestrator.session_log.pop(0)
                self.log_signal.emit(log_entry)

    def _handle_node_output(self, node_name: str, output: dict):
        """Processes real-time feedback from LangGraph nodes."""
        if not output: return
        
        if "screenshot" in output and output["screenshot"]:
            self.screenshot_signal.emit(output["screenshot"])
            
        if "current_step" in output:
            step_text = output["current_step"].upper()
            self.status_signal.emit(step_text)
            
        if "pending_question" in output and output["pending_question"] and node_name == "autonomous_executor":
            if not AUTO_APPROVAL:
                self.speak_signal.emit(output["pending_question"])

    def resume_with_approval(self, approved: bool):
        """Manual trigger from the Dashboard UI."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._resume_logic(approved), self.loop)

    async def _resume_logic(self, approved: bool):
        """Handles manual user intervention for visual edge cases."""
        decision = "approved" if approved else "rejected"
        await self.orchestrator.app.update_state(self.session_config, {"human_approval": decision})
        
        self.log_signal.emit(f"🛡️ USER INTERVENTION: {decision.upper()}")
        self.approval_signal.emit(False)
        
        async for event in self.orchestrator.app.astream(None, config=self.session_config):
            if not self._is_running: return
            for node_name, output in event.items():
                self._sync_orchestrator_logs()
                self._handle_node_output(node_name, output)
        
        self._check_for_interaction()