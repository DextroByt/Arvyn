import pyttsx3
import speech_recognition as sr
import threading
import queue
from typing import Optional
from config import VOICE_RATE, VOICE_VOLUME, VOICE_GENDER_INDEX

class ArvynVoice:
    def __init__(self):
        """Initializes the SAPI5 engine for local audio I/O [cite: 86-89]."""
        # Initialize TTS Engine
        self.tts_engine = pyttsx3.init('sapi5')
        self.tts_engine.setProperty('rate', VOICE_RATE)
        self.tts_engine.setProperty('volume', VOICE_VOLUME)
        
        # Set Voice (David/Zira) [cite: 93-94]
        voices = self.tts_engine.getProperty('voices')
        if len(voices) > VOICE_GENDER_INDEX:
            self.tts_engine.setProperty('voice', voices[VOICE_GENDER_INDEX].id)
        
        # Initialize STT Recognizer
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.mic = sr.Microphone()
        
        # Threading queue for asynchronous speech
        self.speech_queue = queue.Queue()
        self._start_tts_thread()

    def _start_tts_thread(self):
        """Runs the TTS engine in a background thread to prevent GUI blocking."""
        def worker():
            while True:
                text = self.speech_queue.get()
                if text is None: break
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                self.speech_queue.task_done()
        
        threading.Thread(target=worker, daemon=True).start()

    def speak(self, text: str):
        """Queues text to be spoken by the agent[cite: 92, 215]."""
        self.speech_queue.put(text)

    def listen(self) -> Optional[str]:
        """
        Captures audio and transcribes it using SAPI5 [cite: 85-88].
        Returns the transcribed text string or None if not understood.
        """
        with self.mic as source:
            # Adjust for ambient noise for better accuracy
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                print("Arvyn is listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                # Using recognize_google as a fallback/primary for better quality, 
                # but can be switched to recognize_sphinx for 100% offline [cite: 89-90]
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                print("Arvyn could not understand the audio.")
                return None
            except Exception as e:
                print(f"Voice Recognition Error: {e}")
                return None

    def stop(self):
        """Gracefully shuts down the voice engine."""
        self.speech_queue.put(None)