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
    UPGRADED: Enhanced for Qubrid/Qwen-3 Multi-modal synchronization.
    """
    text_received = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        self._is_active = True
        
        self.recognizer.energy_threshold = 300 
        self.recognizer.dynamic_energy_threshold = True

    def stop(self):
        self._is_active = False

    def run(self):
        self.status_signal.emit("LISTENING")
        logger.info("🎙️ VoiceWorker: Microphone active.")
        
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                audio_chunks = []
                
                while self._is_active:
                    try:
                        chunk = self.recognizer.listen(source, timeout=1, phrase_time_limit=4)
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
    UPGRADED: Qubrid/Qwen-3 Zero-Auth Autonomous Execution Engine with Priority Prompting.
    FIXED: Strengthened logic for Rio Finance Bank ecosystem to override default model bias.
    """
    log_signal = pyqtSignal(str)
    screenshot_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    approval_signal = pyqtSignal(bool, bool) # (show, force_manual)
    speak_signal = pyqtSignal(str)
    auto_mic_signal = pyqtSignal(bool)
    finished_signal = pyqtSignal(dict)
    session_signal = pyqtSignal(str, str)

    _shared_checkpointer = MemorySaver()

    # --- ENHANCEMENT: SYSTEM PROMPT DEFINITION (STRENGTHENED FOR QWEN-3) ---
    # This acts as the "Mental Guardrail" to ensure the AI uses the local portal.
    SYSTEM_PROMPT = """
    MANDATORY ROLE: You are Arvyn, a specialized financial automation agent. 
    You must operate EXCLUSIVELY within the 'Rio Finance Bank' portal for the following tasks:
    1. Paying Electricity Bills
    2. Buying Digital Gold
    3. Updating Profile Details
    4. User Login

    PORTAL OVERRIDE: 
    Even if your general knowledge suggests otherwise, for THIS environment, the Target URL for these tasks is ALWAYS: 
    https://roshan-chaudhary13.github.io/rio_finance_bank/

    STRICT RULES:
    - You are in a controlled development test environment. 
    - NEVER suggest external official sites (like Amazon or Utility Providers) for these 4 commands.
    - NEVER use Google Search to find alternative ways to pay these bills.
    - Proceed directly to the Rio Finance Bank portal immediately when these tasks are requested.
    """

    def __init__(self):
        super().__init__()
        self.command_queue = queue.Queue()
        self.orchestrator = None
        self.loop = None
        self._is_running = True
        self.session_config = {"configurable": {"thread_id": "arvyn_autonomous_v4_qubrid"}, "recursion_limit": 100}
        self.approval_timeout_task = None

    def submit_command(self, user_command: str):
        self.command_queue.put(user_command)

    def submit_session_info(self, session_name: str, info_text: str):
        """Thread-safe entrypoint: forward session info to the orchestrator's SessionManager."""
        if not self.loop or not self.orchestrator:
            # Queue a lightweight command fallback if orchestrator not ready
            self.submit_command(f"SESSION_INFO::{session_name}::{info_text}")
            return
        try:
            asyncio.run_coroutine_threadsafe(self._submit_session_info_async(session_name, info_text), self.loop)
        except Exception as e:
            logger.error(f"Failed to submit session info: {e}")

    async def _submit_session_info_async(self, session_name: str, info_text: str):
        try:
            # Update the in-memory session parameters
            sess = getattr(self.orchestrator, 'sessions', None)
            if sess:
                sess.update_session(missing_info=info_text)
                self.log_signal.emit(f"Session updated: {session_name} -> {info_text}")
            else:
                self.log_signal.emit(f"No session manager available to update: {session_name}")
        except Exception as e:
            logger.error(f"_submit_session_info_async error: {e}")

    def stop_persistent_session(self):
        self._is_running = False
        # Do not schedule cleanup here; the run() loop will handle it upon exit
        self.command_queue.put(None)

    def run(self):
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
            logger.error(f"AgentWorker Main Loop Error: {e}")
        finally:
            if self.orchestrator and self.loop:
                try:
                    self.loop.run_until_complete(self.orchestrator.cleanup())
                except Exception as e:
                    logger.error(f"Cleanup during shutdown failed: {e}")
            self._shutdown_loop()

    def _shutdown_loop(self):
        try:
            pending = asyncio.all_tasks(self.loop)
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending))
            self.loop.close()
            logger.info("✅ AgentWorker: Qubrid Engine session closed safely.")
        except Exception as e:
            logger.error(f"Loop Shutdown Error: {e}")

    async def execute_task(self, user_command: str):
        """
        Intelligent Autonomous Task Routing with Qubrid/Qwen-3.
        IMPROVED: Injects the Arvyn System Prompt to maintain project context.
        """
        try:
            state_data = self.orchestrator.app.get_state(self.session_config)
            next_nodes = state_data.next or []

            if "human_interaction_node" in next_nodes:
                self.log_signal.emit(f"RESUMING TASK: {user_command}")
                # REJECTION CHECK: Map negative user input to rejected status
                decision = "rejected" if user_command.lower() in ["reject", "no", "stop", "abort", "cancel"] else "approved"
                
                self.orchestrator.app.update_state(
                    self.session_config, 
                    {"messages": [("user", user_command)], "human_approval": decision}
                )
                
                async for event in self.orchestrator.app.astream(None, config=self.session_config):
                    if not self._is_running: return
                    try:
                        for node_name, output in event.items():
                            self._sync_orchestrator_logs()
                            self._handle_node_output(node_name, output)
                    except RecursionError as re:
                        logger.error(f"Graph recursion error during astream: {re}")
                        self.log_signal.emit(f"⚠️ SYSTEM: Graph recursion error — aborting this task.")
                        self.status_signal.emit("ERROR")
                        return
            else:
                self.status_signal.emit("ANALYZING")
                self.log_signal.emit(f"--- QUBRID-QWEN AUTONOMOUS TASK: {user_command.upper()} ---")
                
                # Reset approval and security flags for the new task
                self.orchestrator.security_locked = False
                
                self.orchestrator.app.update_state(
                    self.session_config, 
                    {"human_approval": None, "is_security_pause": False}
                )

                initial_input = {
                    "messages": [
                        ("system", self.SYSTEM_PROMPT), 
                        ("user", user_command)
                    ]
                }

                async for event in self.orchestrator.app.astream(initial_input, config=self.session_config):
                    if not self._is_running: return
                    try:
                        for node_name, output in event.items():
                            self._sync_orchestrator_logs()
                            self._handle_node_output(node_name, output)
                    except RecursionError as re:
                        logger.error(f"Graph recursion error during astream: {re}")
                        self.log_signal.emit(f"⚠️ SYSTEM: Graph recursion error — aborting this task.")
                        self.status_signal.emit("ERROR")
                        return

            self._check_for_interaction()
                
        except Exception as e:
            logger.error(f"AgentWorker Execution Error: {e}")
            self.log_signal.emit(f"⚠️ SYSTEM ERROR: {str(e)}")
            self.status_signal.emit("ERROR")

    def _check_for_interaction(self):
        state_data = self.orchestrator.app.get_state(self.session_config)
        values = state_data.values or {}
        next_nodes = state_data.next or []

        logger.info(f"🔍 AgentWorker: Checking interaction. Next nodes: {next_nodes}")
        if "human_interaction_node" in next_nodes:
            # HARDENED: Check physical lock from orchestrator OR step status
            is_sec = self.orchestrator.security_locked or values.get("current_step") == "AWAITING PAYMENT APPROVAL"
            
            question = values.get("pending_question")
            logger.info(f"🛡️ AgentWorker: INTERRUPT DETECTED. Security Pause: {is_sec}, Status: {values.get('current_step')}")
            
            if question:
                self.status_signal.emit("NEED HELP")
                self.speak_signal.emit(question)
                self.auto_mic_signal.emit(True) 
            
            # CRITICAL: Ensure the signal is sent to the UI with high priority
            self.approval_signal.emit(True, bool(is_sec))

            # START TIMEOUT if security pause
            if is_sec:
                if self.approval_timeout_task:
                    self.approval_timeout_task.cancel()
                if self.loop and self.loop.is_running():
                    self.approval_timeout_task = self.loop.create_task(self._start_approval_timeout())
        else:
            logger.info("🔍 AgentWorker: No human interaction node pending.")
            analysis = values.get("browser_context", {})
            if analysis.get("action_type") == "FINISHED":
                if values.get("human_approval") == "rejected":
                    self.status_signal.emit("ABORTED")
                else:
                    self.status_signal.emit("COMPLETED")
                
                voice_prompt = analysis.get("voice_prompt")
                if voice_prompt:
                    self.speak_signal.emit(voice_prompt)
            else:
                self.status_signal.emit("READY")

    def _sync_orchestrator_logs(self):
        if hasattr(self.orchestrator, 'session_log'):
            while self.orchestrator.session_log:
                log_entry = self.orchestrator.session_log.pop(0)
                self.log_signal.emit(log_entry)
        # Emit current session info if present
        try:
            sess_mgr = getattr(self.orchestrator, 'sessions', None)
            if sess_mgr:
                s = sess_mgr.get_session()
                if s:
                    missing = s.params.get('missing_info', '') if hasattr(s, 'params') else ''
                    self.session_signal.emit(s.task_type, missing)
        except Exception:
            pass

    def _handle_node_output(self, node_name: str, output: dict):
        if not output: return
        if "screenshot" in output and output["screenshot"]:
            self.screenshot_signal.emit(output["screenshot"])
        
        # --- CONCISE PAUSE: Immediate UI Sync ---
        is_sec = output.get("is_security_pause", False) or self.orchestrator.security_locked
        if is_sec or output.get("current_step") == "AWAITING PAYMENT APPROVAL":
            self.approval_signal.emit(True, True)

        if "current_step" in output:
            step_text = output["current_step"].upper()
            self.status_signal.emit(step_text)
        
        if "pending_question" in output and output["pending_question"] and node_name == "autonomous_executor":
            if not AUTO_APPROVAL:
                self.speak_signal.emit(output["pending_question"])

    def resume_with_approval(self, approved: bool):
        # Cancel any pending timeout
        if self.approval_timeout_task:
            self.approval_timeout_task.cancel()
            self.approval_timeout_task = None
            
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._resume_logic(approved), self.loop)

    async def _resume_logic(self, approved: bool):
        decision = "approved" if approved else "rejected"
        # RELEASE THE HARD LOCK
        self.orchestrator.security_locked = False
        
        self.orchestrator.app.update_state(self.session_config, {"human_approval": decision})
        self.log_signal.emit(f"🛡️ USER INTERVENTION: {decision.upper()}")
        self.approval_signal.emit(False, False)
        async for event in self.orchestrator.app.astream(None, config=self.session_config):
            if not self._is_running: return
            for node_name, output in event.items():
                self._sync_orchestrator_logs()
                self._handle_node_output(node_name, output)
        self._check_for_interaction()

    async def _start_approval_timeout(self):
        try:
            logger.info("⏳ Security Pause: Starting 60s timeout for user approval...")
            await asyncio.sleep(60)
            logger.warning("⏳ Security Timeout: No response from user. Auto-REJECTING task.")
            # Auto-reject via the resume logic
            # We must be careful to call resume_with_approval which is thread-safe wrapper, 
            # OR call _resume_logic directly since we are already in the loop.
            # But resume_with_approval handles thread safety if called from elsewhere. 
            # Since we are IN the loop, we can call _resume_logic directly, BUT resume_with_approval cancels the task...
            # calling resume_with_approval from inside the task that is running is fine (cancel will just explicitly mark it done)
            # safer to just call logic directly but we need to update UI.
            
            # Using the main thread entry point to ensure signals emit correctly
            self.resume_with_approval(False)
            
        except asyncio.CancelledError:
            logger.info("⏳ Security Timeout: Cancelled (User responded).")