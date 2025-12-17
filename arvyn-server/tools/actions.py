from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

# Timeout for individual element interactions
DEFAULT_TIMEOUT = 10000

def click_element(page: Page, selector: str):
    """
    Attempts to click an element using a standard selector.
    Raises PlaywrightTimeoutError on failure to trigger the self-healing cycle.
    """
    try:
        page.click(selector, timeout=DEFAULT_TIMEOUT)
        return True
    except PlaywrightTimeoutError as e:
        # Structured error propagation: The exception is the symbolic trigger
        error_msg = f"SELECTOR_TIMEOUT: Element not found or timed out using selector: {selector}."
        raise PlaywrightTimeoutError(error_msg)
    except Exception as e:
        print(f"An unexpected error occurred during click: {e}")
        raise

def fill_form_field(page: Page, selector: str, value: str):
    """
    Attempts to fill a form field.
    Raises PlaywrightTimeoutError on failure to trigger the self-healing cycle.
    """
    try:
        page.fill(selector, value, timeout=DEFAULT_TIMEOUT)
        return True
    except PlaywrightTimeoutError as e:
        error_msg = f"SELECTOR_TIMEOUT: Field not found or timed out using selector: {selector}."
        raise PlaywrightTimeoutError(error_msg)
    except Exception as e:
        print(f"An unexpected error occurred during fill: {e}")
        raise

def visual_click(page: Page, x: int, y: int):
    """
    Executes a click based on VLM-provided X, Y coordinates, bypassing the DOM structure.
    """
    # Playwright's mouse click is executed relative to the viewport
    page.mouse.click(x, y)