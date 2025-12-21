import asyncio
import logging
import os
import sys
import time

# Ensure project root is on sys.path for local imports
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.browser import ArvynBrowser
from config import SCREENSHOT_PATH

logger = logging.getLogger("diagnostic")

RIO_URL = "https://roshan-chaudhary13.github.io/rio_finance_bank/"

async def run():
    browser = ArvynBrowser(headless=False)
    try:
        await browser.start()
        await browser.navigate(RIO_URL)
        await asyncio.sleep(2)

        # Try a semantic click for the 'Login' button using center coords
        viewport_center_x = 960
        viewport_center_y = 540

        logger.info("Attempting semantic click with hint 'Login'...")
        success = await browser.click_at_coordinates(viewport_center_x, viewport_center_y, element_hint="Login")
        logger.info(f"Click result: {success}")

        # Save a final screenshot
        if not os.path.exists(SCREENSHOT_PATH): os.makedirs(SCREENSHOT_PATH)
        path = os.path.join(SCREENSHOT_PATH, f"diagnostic_result_{int(time.time())}.png")
        page = await browser.ensure_page()
        await page.screenshot(path=path)
        logger.info(f"Saved result screenshot: {path}")

    except Exception as e:
        logger.error(f"Diagnostic run failed: {e}")
    finally:
        try:
            await browser.close()
        except Exception:
            pass

if __name__ == '__main__':
    asyncio.run(run())
