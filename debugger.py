import os
import time
import json
import google.generativeai as genai
from config import Config, logger

def run_diagnostics():
    print("\n" + "="*50)
    print("   AGENT ARVYN: GEMINI 2.5 API DIAGNOSTICS")
    print("="*50)
    
    # 1. Configuration Check
    if not Config.GEMINI_API_KEY:
        print("[FAIL] No API Key found. Check your .env file.")
        return

    print(f"[INFO] Model Target: {Config.GEMINI_MODEL_NAME}")
    print(f"[INFO] API Key: {Config.GEMINI_API_KEY[:5]}...{Config.GEMINI_API_KEY[-5:]}")

    genai.configure(api_key=Config.GEMINI_API_KEY)
    
    # Initialize the model with JSON constraint to match your production logic
    model = genai.GenerativeModel(
        model_name=Config.GEMINI_MODEL_NAME,
        generation_config={"response_mime_type": "application/json"}
    )

    # TEST 1: Connectivity & Basic Generation
    print("\n[STEP 1] Testing Basic Connectivity...")
    try:
        prompt = "Respond with this JSON: {'status': 'online', 'model': 'gemini-2.5'}"
        response = model.generate_content(prompt)
        data = json.loads(response.text)
        print(f"[PASS] API Active. Model confirmed status: {data.get('status')}")
    except Exception as e:
        print(f"[CRITICAL] Connection failed: {e}")
        if "429" in str(e):
            print(">> ERROR: You have hit your Rate Limit (Quota Exceeded).")
        return

    # TEST 2: Structured Intent Parsing (Simulating real Arvyn logic)
    print("\n[STEP 2] Testing Structured Intent Parsing...")
    try:
        test_command = "Open GitHub and check my notifications"
        prompt = f"""
        Identify intent: "{test_command}"
        Return JSON: {{"action": "NAVIGATE", "provider": "GITHUB"}}
        """
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        if result.get("action") == "NAVIGATE" and "GITHUB" in result.get("provider", "").upper():
            print(f"[PASS] Intent correctly parsed: {result}")
        else:
            print(f"[WARN] Intent parsed but unexpected values: {result}")
    except Exception as e:
        print(f"[FAIL] JSON parsing test failed: {e}")

    # TEST 3: Performance/Latency
    print("\n[STEP 3] Testing Latency (3 Rapid Bursts)...")
    for i in range(1, 4):
        start_time = time.time()
        try:
            model.generate_content("Ping")
            elapsed = time.time() - start_time
            print(f"  Request {i}: {elapsed:.2f}s - Success")
        except Exception as e:
            print(f"  Request {i}: FAILED - {e}")
            break

    print("\n" + "="*50)
    print(" DIAGNOSTICS COMPLETE")
    print("="*50)

if __name__ == "__main__":
    run_diagnostics()