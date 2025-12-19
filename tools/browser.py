import asyncio
import base64
import os
import logging
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, ElementHandle
from config import logger, SCREENSHOT_PATH

class ArvynBrowser:
    """
    The kinetic layer of Agent Arvyn.
    Handles high-speed browser automation and visual capture for the VLM.
    """
    
    def __init__(self, headless: bool = False):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = headless

    async def start(self):
        """Initializes the playwright browser instance with anti-detection args."""
        if self.browser:
            return

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--start-maximized", 
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        # Standard high-res viewport for consistent VLM analysis
        self.context = await self.browser.new_context(viewport={'width': 1280, 'height': 800})
        self.page = await self.context.new_page()
        logger.info("Browser engine started successfully.")

    async def navigate(self, url: str):
        """Direct navigation with a wait for network idle to ensure page is loaded."""
        if not self.page:
            await self.start()
        
        try:
            logger.info(f"Navigating to {url}...")
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            logger.error(f"Navigation failed: {e}")

    async def find_and_click(self, selector: str, timeout: int = 10000):
        """Clicks an element using semantic selectors or CSS."""
        try:
            logger.info(f"Attempting click on: {selector}")
            await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            await self.page.click(selector)
            return True
        except Exception as e:
            logger.warning(f"Could not click {selector}: {str(e)}")
            return False

    async def fill_field(self, selector: str, value: str):
        """Directly fills input fields."""
        try:
            await self.page.wait_for_selector(selector, state="visible", timeout=5000)
            await self.page.fill(selector, value)
            logger.info(f"Field {selector} filled.")
            return True
        except Exception as e:
            logger.error(f"Failed to fill field {selector}: {str(e)}")
            return False

    async def get_screenshot_b64(self) -> str:
        """Captures current view for Gemini's VLM analysis."""
        if not self.page:
            return ""
        
        # Ensure screenshot directory exists
        if not os.path.exists(SCREENSHOT_PATH):
            os.makedirs(SCREENSHOT_PATH)

        path = os.path.join(SCREENSHOT_PATH, "current_view.png")
        await self.page.screenshot(path=path)
        
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def click_at_coordinates(self, x: int, y: int):
        """Executes a click at specific coordinates (used by VLM grounding)."""
        if self.page:
            logger.info(f"Executing coordinate-click at ({x}, {y})")
            await self.page.mouse.click(x, y)

    async def close(self):
        """Clean shutdown of all browser resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.browser = None
        self.playwright = None
        logger.info("Browser session terminated.")