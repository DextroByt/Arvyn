import os
import sys
import asyncio
from dotenv import load_dotenv

# ANSI Colors
RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"

async def test_stt_connection(api_key):
    """Tests the AI/STT Engine (Gemini)"""
    print(f"\n{CYAN}--- Testing AI Engine (STT/Cognition) ---{RESET}")
    if not api_key:
        print(f"{RED}FAIL: STT_API_KEY not found in environment.{RESET}")
        return False
        
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Confirm system is online."
        )
        if response.text:
            print(f"{GREEN}PASS: AI Engine is responding.{RESET}")
            return True
    except ImportError:
        print(f"{RED}FAIL: Library 'google-genai' is missing.{RESET}")
        print("Run: pip install google-genai")
    except Exception as e:
        print(f"{RED}FAIL: AI Engine Error:{RESET} {e}")
    return False

async def test_playwright_connection(cdp_port):
    """Tests the Browser Engine (Playwright)"""
    print(f"\n{CYAN}--- Testing Browser Engine (Playwright) ---{RESET}")
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print(f"{RED}FAIL: Library 'playwright' is missing.{RESET}")
        print("Run: pip install playwright")
        return False

    async with async_playwright() as p:
        try:
            # Attempt to attach to the existing Chrome instance
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{cdp_port}")
            
            # Check if we can see the open pages
            if len(browser.contexts) > 0 and len(browser.contexts[0].pages) > 0:
                page_title = await browser.contexts[0].pages[0].title()
                print(f"{GREEN}PASS: Connected to Chrome.{RESET}")
                print(f"      Active Tab Title: {page_title}")
                await browser.close()
                return True
            else:
                print(f"{RED}FAIL: Connected to Chrome, but no open pages found.{RESET}")
                print("      Make sure you have at least one tab open.")
                await browser.close()
                return False
                
        except Exception as e:
            print(f"{RED}FAIL: Could not connect to Chrome.{RESET}")
            print(f"{RED}Error Details:{RESET} {e}")
            print(f"\n{CYAN}Troubleshooting:{RESET}")
            print("1. Did you run 'launch_arvyn_chrome.bat'?")
            print("2. Is that blank Chrome window still open?")
            return False

async def main():
    # Load Environment
    load_dotenv()
    stt_key = os.getenv("STT_API_KEY")
    cdp_port = os.getenv("CDP_DEBUG_PORT", "9222")

    print(f"{CYAN}=== Arvyn Component Debugger ==={RESET}")
    
    # Run Tests
    ai_status = await test_stt_connection(stt_key)
    browser_status = await test_playwright_connection(cdp_port)

    # Summary
    print(f"\n{CYAN}=== Debug Summary ==={RESET}")
    if ai_status and browser_status:
        print(f"{GREEN}All systems GO. The 503 error might be in the request payload.{RESET}")
    elif not browser_status:
        print(f"{RED}CRITICAL: Browser connection failed.{RESET}")
        print("The 503 error is because the server cannot talk to Chrome.")
    elif not ai_status:
        print(f"{RED}CRITICAL: AI/STT connection failed.{RESET}")
        print("The 503 error is because the server cannot transcribe the audio.")

if __name__ == "__main__":
    asyncio.run(main())