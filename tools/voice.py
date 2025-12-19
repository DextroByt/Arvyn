import pyttsx3
import speech_recognition as sr
import threading
import asyncio
from config import logger, DEFAULT_VOICE_ID, COMMAND_TIMEOUT

class ArvynVoice:
    """
    The sensory interface for Agent Arvyn (Production Grade).
    Refined as a thread-safe utility for TTS and secondary audio capture.
    """

    def __init__(self):
        self._lock = threading.Lock() 
        self._is_speaking = False
        self.engine = None
        
        # Initialize TTS Engine with error recovery
        self._init_engine()

        # Initialize Recognizer utility
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300  
        self.recognizer.pause_threshold = 0.5   
        logger.info("Voice Utility initialized.")

    def _init_engine(self):
        """Initializes or resets the pyttsx3 engine."""
        try:
            self.engine = pyttsx3.init() if DEFAULT_VOICE_ID is None else pyttsx3.init(DEFAULT_VOICE_ID)
            self.engine.setProperty('rate', 185)
            self.engine.setProperty('volume', 1.0)
            
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if "female" in voice.name.lower() or "zira" in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            logger.info("TTS engine ready.")
        except Exception as e:
            logger.error(f"TTS Initialization Error: {e}")
            self.engine = None

    def speak(self, text: str):
        """
        Thread-safe speech synthesis.
        Prevents 'run loop already started' by checking engine state and using a lock.
        """
        if not text or not self.engine:
            return
        
        def _run_tts():
            # Acquire lock to ensure only one thread controls the pyttsx3 loop
            if not self._lock.acquire(blocking=False):
                logger.warning("TTS is already active. Skipping overlapping speech.")
                return

            self._is_speaking = True
            try:
                # We stop any pending speech before starting new one
                self.engine.stop()
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS Thread Error: {e}")
                # If the loop hangs, try re-initializing for next time
                self._init_engine()
            finally:
                self._is_speaking = False
                self._lock.release()

        threading.Thread(target=_run_tts, daemon=True).start()

    async def listen(self) -> str:
        """
        Secondary STT utility for quick captures.
        Primary manual-toggle recording is now handled by VoiceWorker in threads.py.
        """
        try:
            with sr.Microphone() as source:
                logger.info("Voice Utility: Capturing audio...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                
                audio = await asyncio.to_thread(
                    self.recognizer.listen, 
                    source, 
                    timeout=COMMAND_TIMEOUT, 
                    phrase_time_limit=10
                )
                
                text = await asyncio.to_thread(self.recognizer.recognize_google, audio)
                return text.strip()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return ""
        except Exception as e:
            logger.error(f"Voice Utility STT Error: {e}")
            return ""

    @property
    def is_speaking(self):
        return self._is_speaking