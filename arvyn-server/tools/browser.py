# arvyn-server/tools/browser.py

import requests
from playwright.async_api import async_playwright
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionError(Exception):
    """Raised when the browser connection fails."""
    pass

class PageContextPlaceholder:
    def __init__(self, page):
        self.page = page

def init_browser_connection():
    """
    Connects to an existing Chrome instance running with remote debugging.
    """
    try:
        # 1. Fetch the dynamic WebSocket URL
        response = requests.get("http://127.0.0.1:9222/json/version", timeout=2)
        if response.status_code != 200:
            raise ConnectionError(f"Could not connect to Chrome Debugger. Status: {response.status_code}")
        
        data = response.json()
        ws_url = data.get("webSocketDebuggerUrl")
        
        if not ws_url:
            raise ConnectionError("No webSocketDebuggerUrl found. Is Chrome running with --remote-debugging-port=9222?")

        logger.info(f"Connecting to Chrome via: {ws_url}")

        # 2. Connect Playwright to this specific WebSocket URL
        # Note: We need to use a synchronous approach or handle the async properly in main.py
        # Since this function is called inside an async route in main.py, it should return the object
        # but the actual connection logic usually requires `await`.
        # However, Playwright's `connect_over_cdp` is async.
        
        # NOTE: This function needs to be ASYNC to work with main.py
        # We will fix main.py to await this function.
        return ws_url

    except requests.exceptions.ConnectionError:
        raise ConnectionError("Could not reach http://127.0.0.1:9222. Is Chrome running?")