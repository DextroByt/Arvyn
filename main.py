import os
import logging
from dotenv import load_dotenv
from arvyn_core import ArvynBrain  # Your working brain class
import speech_recognition as sr

# Set logging based on .env
load_dotenv()
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
logger = logging.getLogger("ArvynMain")

def listen_to_user():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        logger.info("Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            text = recognizer.recognize_google(audio)
            return text
        except Exception:
            return None

def main():
    brain = ArvynBrain()
    logger.info("Arvyn System Booted. Ready for voice command.")
    
    while True:
        user_text = listen_to_user()
        
        if user_text:
            logger.info(f"User said: {user_text}")
            if "exit" in user_text.lower() or "stop" in user_text.lower():
                print("Arvyn: Shutting down.")
                break
            
            response = brain.speak(user_text)
            print(f"\nArvyn: {response}\n")
        else:
            # Silent loop to keep the program alive
            pass

if __name__ == "__main__":
    main()