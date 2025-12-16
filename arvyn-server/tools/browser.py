# arvyn-server/tools/browser.py

import os
from playwright.sync_api import sync_playwright, Page, Browser
from playwright.errors import Error as PlaywrightError

CDP_DEBUG_PORT = os.getenv("CDP_DEBUG_PORT", "9222")
CDP_URL = f"http://localhost:{CDP_DEBUG_PORT}"

class ConnectionError(Exception):
    """Custom exception for structured CDP connection failures."""
    pass

class PageContextPlaceholder:
    """A wrapper class to hold the non-serializable Playwright Page object reference."""
    def __init__(self, page_ref: Page):
        self.page = page_ref
    def __getattr__(self, name):
        """Allows direct attribute access to the underlying Page object."""
        return getattr(self.page, name)

def init_browser_connection() -> Page:
    """
    Connects Playwright to the active Chrome instance via CDP.
    Raises ConnectionError if the browser or page context is inaccessible.
    """
    pw = None
    try:
        pw = sync_playwright().start()
        # Connect to the external Chrome instance 
        browser: Browser = pw.chromium.connect_over_cdp(CDP_URL)
        
        contexts = browser.contexts()
        if not contexts:
            raise ConnectionError("CDP_DISCONNECTED: No browser context found via CDP.")
            
        default_context = contexts
        pages = default_context.pages()
        
        if not pages:
            raise ConnectionError("CDP_DISCONNECTED: No active page found in the default context.")
            
        page = pages # The assumed target banking page
        
        # Test connection health by retrieving title
        page.title() 
        
        return page

    except PlaywrightError as e:
        # Detect connection loss or closure exceptions
        if "connect" in str(e).lower() or "connection closed" in str(e).lower() or "target closed" in str(e).lower():
            raise ConnectionError(f"CDP_DISCONNECTED: Critical loss of connection to Chrome process. Details: {e}")
        else:
            raise ConnectionError(f"UNEXPECTED_CDP_ERROR: {e}")
    except Exception as e:
        raise ConnectionError(f"Unexpected error during CDP initiation: {e}")
    finally:
        # NOTE: Do NOT stop pw here, as the page object must remain active for the graph execution
        pass 


