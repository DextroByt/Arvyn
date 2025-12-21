import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_qubrid_multimodal():
    # Fetch from .env
    url = os.getenv("QUBRID_BASE_URL")
    api_key = os.getenv("QUBRID_API_KEY")
    model = os.getenv("QUBRID_MODEL_NAME")

    print(f"--- Qubrid Multimodal Diagnostic ---")
    print(f"[*] Endpoint: {url}")
    print(f"[*] Model: {model}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Test payload with a public image to verify vision logic
    data = {
        "model": model,
        "messages": [
            {
                "role": "user", 
                "content": [
                    {
                        "type": "text", 
                        "text": "Describe this image in one sentence."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.7,
        "max_tokens": 100,
        "stream": False
    }

    try:
        print("[*] Contacting Qubrid Multimodal Engine...")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content']
            print(f"\n[SUCCESS] API Vision Response: {answer}")
        else:
            print(f"\n[FAILED] Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            
    except Exception as e:
        print(f"\n[CRITICAL] Script Error: {str(e)}")

if __name__ == "__main__":
    test_qubrid_multimodal()