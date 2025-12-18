import speech_recognition as sr

def test_microphone():
    recognizer = sr.Recognizer()
    print("--- [ Ears Diagnostic ] ---")
    print("Available Microphones:", sr.Microphone.list_microphone_names())
    
    with sr.Microphone() as source:
        print("\n[!] Please say something now...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=5)
            print("[+] Audio captured. Processing...")
            text = recognizer.recognize_google(audio)
            print(f"[✅] I heard: '{text}'")
        except Exception as e:
            print(f"[❌] Error: {e}")

if __name__ == "__main__":
    test_microphone()