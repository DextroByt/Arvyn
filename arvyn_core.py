import os
import webbrowser
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Define the actual 'Hand' (The Function)
def open_browser(url: str):
    """Opens a specific URL in the default web browser (Chrome)."""
    print(f"--- [ACTION] Opening Browser: {url} ---")
    webbrowser.open(url)
    return f"Successfully opened {url} in Chrome."

class ArvynBrain:
    def __init__(self):
        load_dotenv()
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-2.5-flash"
        
        # 2. Register the tool so Arvyn knows it can use it
        self.tools = [open_browser]
        
        self.config = types.GenerateContentConfig(
            system_instruction="""
            You are Arvyn from IIT Bombay. 
            You have the power to control the user's browser.
            If a user asks to 'open chrome' or 'search for something', 
            use the 'open_browser' tool with a Google search URL.
            """,
            tools=self.tools,
            # Automatic Function Calling (AFC) handles the execution for you
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
        )
        
        self.chat = self.client.chats.create(
            model=self.model_id,
            config=self.config
        )

    def speak(self, message: str):
        try:
            # AFC will automatically run open_browser if Arvyn decides to
            response = self.chat.send_message(message)
            return response.text
        except Exception as e:
            return f"⚠️ Agent Error: {e}"