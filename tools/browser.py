import base64
import asyncio
from typing import Optional, Dict
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from config import HEADLESS_MODE, BROWSER_TIMEOUT, USER_AGENT

class ArvynBrowser:
    def __init__(self):
        """Initializes the Playwright automation engine."""
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start(self):
        """Launches the Chromium instance with direct CDP support."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS_MODE,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.context = await self.browser.new_context(user_agent=USER_AGENT)
        self.page = await self.context.new_page()
        self.page.set_default_timeout(BROWSER_TIMEOUT)

    async def navigate(self, url: str):
        """Navigates with 'networkidle' wait to ensure full page hydration."""
        if self.page:
            await self.page.goto(url, wait_until="networkidle")

    async def smart_click(self, selector: str):
        """
        Executes a click using semantic targeting and Shadow DOM piercing.
        Playwright automatically waits for actionability (visible, stable, enabled).
        """
        # Prioritize role-based semantic selectors for stability
        try:
            # Chained locator for Shadow DOM support is native in Playwright CSS/Text engines
            locator = self.page.locator(selector)
            await locator.click()
            return True
        except Exception as e:
            print(f"DOM Click Failed: {e}. Switching to alternate strategies...")
            return False

    async def fill_field(self, selector: str, value: str):
        """Fills a form field after ensuring it is ready for input."""
        await self.page.locator(selector).fill(value)

    async def get_screenshot_b64(self) -> str:
        """Captures the current viewport for Explorer Mode visual analysis."""
        screenshot_bytes = await self.page.screenshot(type="png")
        return base64.b64encode(screenshot_bytes).decode("utf-8")

    async def click_at_coordinates(self, x_norm: float, y_norm: float):
        """
        Explorer Mode: Executes a physical mouse click at normalized coordinates.
        This bypasses the DOM entirely, acting as a 'Self-Healing' fallback.
        """
        viewport = self.page.viewport_size
        if viewport:
            x = x_norm * viewport['width']
            y = y_norm * viewport['height']
            await self.page.mouse.click(x, y)

    async def scrape_page_content(self) -> str:
        """Extracts text for Gemini to analyze the financial state."""
        return await self.page.content()

    async def stop(self):
        """Gracefully closes the browser session."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()