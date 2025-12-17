# arvyn-server/tools/browser.py
import os
from typing import Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext, Browser, Playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# --- Configuration ---
# CDP_DEBUG_PORT must match the port the user launches Chrome with (e.g., 9222)
CDP_DEBUG_PORT: str = os.getenv("CDP_DEBUG_PORT", "9222")
CDP_URL: str = f"http://localhost:{CDP_DEBUG_PORT}"

# --- Custom Exceptions for Structured Error Trapping (Mitigation 3.3.A) ---
class ConnectionError(Exception):
    """Custom exception for structured CDP connection failures (e.g., CDP_DISCONNECTED)."""
    pass

# --- Helper Class for Non-Serializable Object Reference ---
class PageContextPlaceholder:
    """
    A wrapper class to hold the non-serializable Playwright Page object reference.
    This allows the Page object to be passed persistently across LangGraph checkpoints 
    without serialization issues.
    """
    def __init__(self, page_ref: Page):
        self.page: Page = page_ref
    
    def __getattr__(self, name: str):
        """Allows direct attribute access to the underlying Page object (e.g., page_context.goto())."""
        return getattr(self.page, name)
    
    # Define a repr for better debugging
    def __repr__(self):
        return f"<PageContextPlaceholder for Page with URL: {getattr(self.page, 'url', 'N/A')}>"

# --- Connection Logic ---
def init_browser_connection() -> Page:
    """
    Connects Playwright to the active Chrome instance via CDP.
    Raises ConnectionError if the browser or page context is inaccessible.
    """
    pw: Optional[Playwright] = None
    try:
        # 1. Start Playwright Sync Context
        pw = sync_playwright().start() 
        
        # 2. Connect to the external Chrome instance via CDP
        # This targets the browser launched by the user with the --remote-debugging-port flag
        browser: Browser = pw.chromium.connect_over_cdp(CDP_URL)
        
        # 3. Retrieve the active browser context and page
        contexts: list[BrowserContext] = browser.contexts()
        if not contexts:
            raise ConnectionError("CDP_DISCONNECTED: No browser context found via CDP. Check if Chrome is open.")
            
        # Assume the first context is the one with the target banking page
        default_context: BrowserContext = contexts[0]
        pages: list[Page] = default_context.pages()
        
        if not pages:
            raise ConnectionError("CDP_DISCONNECTED: No active page found in the default context. Navigate to target bank.")
            
        # The target page is the first (and usually only) active page
        page: Page = pages[0] 
        
        # 4. Test connection health by retrieving a basic property
        page.title()
        
        return page
        
    except PlaywrightError as e:
        # Explicit Error Trap for Connection Loss (Mitigation 3.3.A)
        error_str = str(e).lower()
        if "connect" in error_str or "connection closed" in error_str or "target closed" in error_str:
            # Raise structured exception for main.py to catch and push status to Sidecar
            raise ConnectionError(f"CDP_DISCONNECTED: Critical loss of connection to Chrome process. Details: {e}") from e
        else:
            # Catch other unexpected Playwright errors
            raise ConnectionError(f"UNEXPECTED_PLAYWRIGHT_ERROR: {e}") from e
    except ConnectionError:
        # Re-raise the structured error
        raise
    except Exception as e:
        # Catch unexpected errors during initiation
        raise ConnectionError(f"UNEXPECTED_INIT_ERROR: {e}") from e
    finally:
        # NOTE: Do NOT stop pw here, as the page object must remain active for the graph execution
        pass