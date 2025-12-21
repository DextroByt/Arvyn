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
    v4.1 OPTIMIZED: Accelerated calibration and latency-tuned transcription.
    MAINTAINED: Adaptive noise logic and high-accuracy Google Web Speech.
    """
    text_received = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        self._is_active = True
        
        # Latency-tuned thresholds for faster response
        self.recognizer.energy_threshold = 300 
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8 # Reduced from 1.2 for snappier cutoff
        self.recognizer.non_speaking_duration = 0.4

    def stop(self):
        """Forces the recording loop to terminate and begin transcription."""
        self._is_active = False

    def run(self):
        self.status_signal.emit("LISTENING")
        logger.info("🎙️ VoiceWorker: Active. Accelerated monitoring enabled.")
        
        try:
            with self.mic as source:
                # SPEED: Reduced calibration from 1.2s to 0.6s for faster trigger
                self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                audio_chunks = []
                
                while self._is_active:
                    try:
                        # Tightened timeout for higher responsiveness
                        chunk = self.recognizer.listen(source, timeout=0.5, phrase_time_limit=4)
                        audio_chunks.append(chunk)
                    except sr.WaitTimeoutError:
                        continue
                
                if not audio_chunks:
                    self.text_received.emit("")
                    return

                # Fast buffer compilation
                combined_audio = sr.AudioData(
                    b"".join([c.get_raw_data() for c in audio_chunks]),
                    audio_chunks[0].sample_rate,
                    audio_chunks[0].sample_width
                )

            self.status_signal.emit("ANALYZING")
            # Google API call remains the standard for accuracy
            text = self.recognizer.recognize_google(combined_audio)
            
            if text:
                logger.info(f"🗣️ Voice Layer: Decoded '{text}'")
                self.text_received.emit(text)
            else:
                self.text_received.emit("")
                
        except sr.UnknownValueError:
            self.status_signal.emit("RETRY")
            self.text_received.emit("")
        except Exception as e:
            logger.error(f"Voice Latency Error: {e}")
            self.status_signal.emit("ERROR")
            self.text_received.emit("")

class AgentWorker(QThread):
    """
    Superior Session Orchestration Worker.
    v4.1 UPGRADED: Accelerated Stream Processing and GPU Warmup logic.
    MAINTAINED: Autonomous Logic, Memory Persistence, and High-Fidelity Logging.
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
        # Updated session configuration for v4.1 optimizations
        self.session_config = {"configurable": {"thread_id": "arvyn_ultra_speed_v4"}}

    def submit_command(self, user_command: str):
        self.command_queue.put(user_command)

    def stop_persistent_session(self):
        self._is_running = False
        if self.orchestrator and self.loop:
            asyncio.run_coroutine_threadsafe(self.orchestrator.cleanup(), self.loop)
        self.command_queue.put(None)

    def run(self):
        """Initializes the VLM environment with speed-focused warmups."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.status_signal.emit("BOOTING")
        self.log_signal.emit("SYSTEM: Initializing Optimized 4-Bit AI Brain...")
        
        try:
            self.orchestrator = ArvynOrchestrator()
            self.status_signal.emit("PREPARING")
            self.loop.run_until_complete(self.orchestrator.init_app(self._shared_checkpointer))
            
            # --- SPEED IMPROVEMENT: GPU WARMUP ---
            # Triggering a tiny intent parse to pre-load CUDA kernels and cache
            self.log_signal.emit("SYSTEM: Warming up CUDA kernels for zero-latency execution...")
            self.loop.run_until_complete(self.orchestrator.brain.parse_intent("warmup"))
            
            self.status_signal.emit("READY")
            self.log_signal.emit("✅ SYSTEM: Arvyn Core v4.1 [Ultra Speed] Online.")
            
            while self._is_running:
                command = self.command_queue.get()
                if command is None: break 
                
                # Execute with timestamp for latency auditing
                start_time = time.time()
                self.loop.run_until_complete(self.execute_task(command))
                end_time = time.time()
                
                logger.info(f"[PERF] Task completed in {end_time - start_time:.2f}s")
                self.command_queue.task_done()
                
        except Exception as e:
            logger.error(f"AgentWorker Main Failure: {e}")
            self.log_signal.emit(f"⚠️ SYSTEM ERROR: {str(e)}")
            self.status_signal.emit("FAULT")
        finally:
            self._shutdown_loop()

    def _shutdown_loop(self):
        try:
            pending = asyncio.all_tasks(self.loop)
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending))
            self.loop.close()
            logger.info("✅ AgentWorker: Resources released.")
        except Exception as e:
            logger.error(f"Shutdown Fault: {e}")

    async def execute_task(self, user_command: str):
        """Accelerated Task Streamer."""
        try:
            self.status_signal.emit("THINKING")
            self.log_signal.emit(f"--- GOAL: {user_command.upper()} ---")
            
            initial_input = {"messages": [("user", user_command)]}

            # SPEED: Use a prioritized stream handler
            async for event in self.orchestrator.app.astream(initial_input, config=self.session_config):
                if not self._is_running: return
                for node_name, output in event.items():
                    # Process signals in parallel where possible
                    self._sync_orchestrator_logs()
                    self._handle_node_output(node_name, output)
                    # Yield to loop to prevent GUI freezing during heavy VLM batching
                    await asyncio.sleep(0.005) 

            self._check_final_state()
                
        except Exception as e:
            logger.error(f"Execution Error: {e}")
            self.log_signal.emit(f"⚠️ ERROR: {str(e)}")
            self.status_signal.emit("READY")

    def _check_final_state(self):
        state_data = self.orchestrator.app.get_state(self.session_config)
        values = state_data.values or {}
        voice_msg = values.get("pending_question") or values.get("browser_context", {}).get("voice_prompt")
        if voice_msg:
            self.speak_signal.emit(voice_msg)
        self.status_signal.emit("READY")

    def _sync_orchestrator_logs(self):
        """Batch-pipes high-speed session logs to the Dashboard."""
        if hasattr(self.orchestrator, 'session_log'):
            # SPEED: Log batching to reduce UI signal overhead
            logs_to_emit = []
            while self.orchestrator.session_log:
                logs_to_emit.append(self.orchestrator.session_log.pop(0))
            
            for log in logs_to_emit:
                self.log_signal.emit(log)
                if "Injecting secure data" in log:
                    self.approval_signal.emit(True)

    def _handle_node_output(self, node_name: str, output: dict):
        if not output: return
        
        # SPEED: Immediate screenshot refresh
        if "screenshot" in output and output["screenshot"]:
            self.screenshot_signal.emit(output["screenshot"])
            
        if "current_step" in output:
            self.status_signal.emit(output["current_step"].upper())
            
        analysis = output.get("browser_context", {})
        if analysis.get("voice_prompt"):
            self.speak_signal.emit(analysis["voice_prompt"])

    def resume_with_approval(self, approved: bool):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._resume_logic(approved), self.loop)

    async def _resume_logic(self, approved: bool):
        decision = "approved" if approved else "rejected"
        await self.orchestrator.app.update_state(self.session_config, {"human_approval": decision})
        self.approval_signal.emit(False)