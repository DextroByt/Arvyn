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
    approval_signal = pyqtSignal(bool)
    speak_signal = pyqtSignal(str)
    auto_mic_signal = pyqtSignal(bool)
    finished_signal = pyqtSignal(dict)

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
        self.session_config = {"configurable": {"thread_id": "arvyn_autonomous_v4_qubrid"}}

    def submit_command(self, user_command: str):
        self.command_queue.put(user_command)

    def stop_persistent_session(self):
        self._is_running = False
        if self.orchestrator and self.loop:
            asyncio.run_coroutine_threadsafe(self.orchestrator.cleanup(), self.loop)
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
                self.status_signal.emit("ANALYZING")
                self.log_signal.emit(f"--- QUBRID-QWEN AUTONOMOUS TASK: {user_command.upper()} ---")
                
                # Prepend the system prompt to the message stack for the LLM
                initial_input = {
                    "messages": [
                        ("system", self.SYSTEM_PROMPT), 
                        ("user", user_command)
                    ]
                }

                async for event in self.orchestrator.app.astream(initial_input, config=self.session_config):
                    if not self._is_running: return
                    for node_name, output in event.items():
                        self._sync_orchestrator_logs()
                        self._handle_node_output(node_name, output)

            self._check_for_interaction()
                
        except Exception as e:
            logger.error(f"AgentWorker Execution Error: {e}")
            self.log_signal.emit(f"⚠️ SYSTEM ERROR: {str(e)}")
            self.status_signal.emit("ERROR")

    def _check_for_interaction(self):
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
        if hasattr(self.orchestrator, 'session_log'):
            while self.orchestrator.session_log:
                log_entry = self.orchestrator.session_log.pop(0)
                self.log_signal.emit(log_entry)

    def _handle_node_output(self, node_name: str, output: dict):
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
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._resume_logic(approved), self.loop)

    async def _resume_logic(self, approved: bool):
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