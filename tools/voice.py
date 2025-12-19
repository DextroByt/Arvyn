import pyttsx3
import speech_recognition as sr
import threading
import asyncio
from config import logger, DEFAULT_VOICE_ID, COMMAND_TIMEOUT

class ArvynVoice:
    """
    The sensory interface for Agent Arvyn.
    Handles Speech-to-Text (STT) and Text-to-Speech (TTS).
    """

    def __init__(self):
        # Initialize threading lock to prevent overlapping TTS loops
        self._lock = threading.Lock() 
        
        # Initialize TTS Engine
        try:
            self.engine = pyttsx3.init() if DEFAULT_VOICE_ID is None else pyttsx3.init(DEFAULT_VOICE_ID)
            self.engine.setProperty('rate', 185)  # Natural assistant speed
            self.engine.setProperty('volume', 1.0)
            
            # Persona: Search for a female voice
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if "female" in voice.name.lower() or "zira" in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            logger.info("TTS engine initialized successfully.")
        except Exception as e:
            logger.error(f"TTS Initialization Error: {e}")

        # Initialize Recognizer
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300  
        self.recognizer.pause_threshold = 0.5   # Rapid response after user stops talking
        self._is_speaking = False

    def speak(self, text: str):
        """Synthesizes speech using a thread-safe lock to avoid RuntimeErrors."""
        if not text: return
        
        def _run():
            # The lock ensures only one thread controls the pyttsx3 loop at a time
            with self._lock:
                self._is_speaking = True
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    logger.error(f"TTS Thread Error: {e}")
                finally:
                    self._is_speaking = False

        # Run as a daemon thread so it doesn't hang the application on exit
        threading.Thread(target=_run, daemon=True).start()

    async def listen(self) -> str:
        """Listens and transcribes audio into text for direct commands."""
        with sr.Microphone() as source:
            logger.info("Microphone active...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            
            try:
                # Listen with a timeout to maintain responsiveness
                audio = await asyncio.to_thread(
                    self.recognizer.listen, 
                    source, 
                    timeout=COMMAND_TIMEOUT, 
                    phrase_time_limit=10
                )
                
                logger.info("Transcribing audio...")
                text = await asyncio.to_thread(self.recognizer.recognize_google, audio)
                logger.info(f"Captured Command: {text}")
                return text.strip()
                
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                return ""
            except Exception as e:
                logger.error(f"Speech Recognition Error: {e}")
                return ""

    @property
    def is_speaking(self):
        return self._is_speaking