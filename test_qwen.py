import os
import requests
import json
from dotenv import load_dotenv

# 1. Load the .env file
load_dotenv()

def test_qwen_connection():
    api_key = os.getenv("QWEN_API_KEY")
    base_url = os.getenv("QWEN_BASE_URL")
    model_name = os.getenv("QWEN_MODEL_NAME")

    print("--- Arvyn Logic Engine Diagnostic ---")
    print(f"[*] Targeting Model: {model_name}")
    print(f"[*] Base URL: {base_url}")
    
    # Check if key exists
    if not api_key:
        print("[!] ERROR: QWEN_API_KEY not found in .env file.")
        return

    # Prepare the payload (Simulating an Intent Parsing request)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "Identify the intent of this command: 'Pay my electricity bill'"
            }
        ]
    }

    print("[*] Sending request to DashScope...")

    try:
        # We use /chat/completions as per your log's "compatible-mode"
        endpoint = f"{base_url}/chat/completions"
        response = requests.post(endpoint, headers=headers, json=payload)
        
        if response.status_code == 200:
            print("\n[SUCCESS] API is working!")
            data = response.json()
            print(f"[RESPONSE]: {data['choices'][0]['message']['content']}")
        elif response.status_code == 401:
            print("\n[FAILED] Error 401: Unauthorized.")
            print("REASON: Your API Key is likely invalid or has expired.")
            print(f"DEBUG INFO: {response.text}")
        else:
            print(f"\n[FAILED] Error {response.status_code}")
            print(f"RESPONSE: {response.text}")

    except Exception as e:
        print(f"\n[CRITICAL] Connection Error: {str(e)}")

if __name__ == "__main__":
    test_qwen_connection()