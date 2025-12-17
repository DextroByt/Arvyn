# arvyn-server/tools/actions.py
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
# Timeout for individual element interactions (in milliseconds)
DEFAULT_TIMEOUT = 10000 

def click_element(page: Page, selector: str) -> bool:
    """
    Attempts to click an element using a standard CSS selector.
    Raises PlaywrightTimeoutError on failure to trigger the self-healing cycle.
    """
    try:
        # Playwright's auto-waiting is implicitly used
        page.click(selector, timeout=DEFAULT_TIMEOUT)
        return True
    except PlaywrightTimeoutError as e:
        # Structured error propagation: The exception is the symbolic trigger 
        error_msg = f"SELECTOR_TIMEOUT: Element not found or timed out using selector: {selector}."
        # Re-raise the structured error with a clear message for the graph state
        raise PlaywrightTimeoutError(error_msg) from e
    except Exception as e:
        # Handle unexpected runtime errors during the click action
        print(f"An unexpected error occurred during click: {e}")
        raise

def fill_form_field(page: Page, selector: str, value: str) -> bool:
    """
    Attempts to fill a form field using a standard selector.
    Raises PlaywrightTimeoutError on failure to trigger the self-healing cycle.
    """
    try:
        page.fill(selector, value, timeout=DEFAULT_TIMEOUT)
        return True
    except PlaywrightTimeoutError as e:
        # Structured error propagation: This is the symbolic trigger [cite: 132, 140]
        error_msg = f"SELECTOR_TIMEOUT: Field not found or timed out using selector: {selector}."
        # Re-raise the structured error
        raise PlaywrightTimeoutError(error_msg) from e
    except Exception as e:
        # Handle unexpected runtime errors during the fill action
        print(f"An unexpected error occurred during fill: {e}")
        raise

def visual_click(page: Page, x: int, y: int):
    """
    Executes a direct mouse click based on VLM-provided X, Y coordinates, 
    effectively bypassing the DOM structure when selectors fail. [cite: 134, 140]
    """
    # Playwright's mouse click is executed relative to the viewport
    # This is the final action of the Neuro pathway. [cite: 133, 140]
    page.mouse.click(x, y)