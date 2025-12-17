import requests
import wave
import struct
import os
import sys

# Configuration
URL = "http://127.0.0.1:8000/command"
TEST_AUDIO_FILE = "test_audio.wav"

def create_dummy_audio():
    """Generates a valid, short WAV file (1 second of silence) for testing."""
    print("Generating dummy audio file...")
    try:
        with wave.open(TEST_AUDIO_FILE, 'w') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(44100)
            f.setnframes(44100)
            # Write 1 second of silence
            data = struct.pack('<h', 0) * 44100
            f.writeframes(data)
    except Exception as e:
        print(f"Error creating audio file: {e}")
        sys.exit(1)

def send_request():
    print(f"Sending POST request to {URL}...")
    
    # Check if server is up first
    try:
        requests.get("http://127.0.0.1:8000/docs", timeout=2)
    except requests.exceptions.ConnectionError:
        print("\033[91mCRITICAL ERROR: The Server is NOT running.\033[0m")
        print("You must start the server in a SEPARATE terminal before running this test.")
        print("Command: uvicorn main:app --reload")
        print("OR:      python main.py")
        return

    try:
        # Open file in context manager to ensure it closes properly
        with open(TEST_AUDIO_FILE, 'rb') as f:
            # FIXED: Changed key from 'file' to 'audio_file' to match your main.py requirement
            files = {'audio_file': (TEST_AUDIO_FILE, f, 'audio/wav')}
            
            response = requests.post(URL, files=files)
            
            print(f"\nResponse Status: {response.status_code}")
            
            if response.status_code == 200:
                print("\033[92mSUCCESS! The server processed the audio correctly.\033[0m")
                print("Response:", response.json())
            elif response.status_code == 503:
                print("\033[91mFAILURE: 503 Service Unavailable\033[0m")
                print("The server crashed internally.")
                print("Action: Look at the TERMINAL where 'python main.py' is running. Copy the Error/Traceback.")
            elif response.status_code == 422:
                print("\033[93mFAILURE: 422 Validation Error\033[0m")
                print("The server expected a different file format or field name.")
                print("Response:", response.json())
            else:
                print(f"FAILURE: Unexpected Status {response.status_code}")
                print("Response:", response.text)
            
    except Exception as e:
        print(f"Error sending request: {e}")
    finally:
        # Cleanup - now safe because file is closed
        if os.path.exists(TEST_AUDIO_FILE):
            try:
                os.remove(TEST_AUDIO_FILE)
            except PermissionError:
                print(f"Warning: Could not delete {TEST_AUDIO_FILE} (still in use).")

if __name__ == "__main__":
    create_dummy_audio()
    send_request()