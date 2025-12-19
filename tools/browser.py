import asyncio
import base64
import os
import logging
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, ElementHandle
from config import logger, SCREENSHOT_PATH

class ArvynBrowser:
    """
    The kinetic layer of Agent Arvyn (Production Grade).
    Enhanced with Dynamic Viewport Detection to support different laptop screens.
    """
    
    def __init__(self, headless: bool = False):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = headless
        
        # Default internal playground size
        self.viewport_width = 1280
        self.viewport_height = 800

    async def start(self):
        """Initializes the browser with anti-detection and a stable viewport."""
        if self.browser:
            return

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--start-maximized", 
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        
        # Using a fixed internal context ensures Gemini's vision is consistent,
        # but we provide methods to get actual dimensions for different screen types.
        self.context = await self.browser.new_context(
            viewport={'width': self.viewport_width, 'height': self.viewport_height},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        logger.info(f"Intelligent Browser Engine started at {self.viewport_width}x{self.viewport_height}.")

    async def get_dimensions(self) -> Dict[str, int]:
        """
        Dynamically retrieves the actual current viewport size.
        Used to solve the 'Different Laptop' resolution error.
        """
        if self.page:
            size = self.page.viewport_size
            if size:
                return size
        return {"width": self.viewport_width, "height": self.viewport_height}

    async def navigate(self, url: str):
        """Navigates with a safety buffer for dynamic content loading."""
        if not self.page:
            await self.start()
        
        try:
            logger.info(f"Navigating to {url}...")
            # 'networkidle' is used here to ensure the search results or site are fully rendered
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1) 
        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")

    async def click_at_coordinates(self, x: int, y: int):
        """
        Executes a precise mouse click at calculated (x, y) pixels.
        Includes human-like mouse movement to avoid bot detection.
        """
        if self.page:
            try:
                logger.info(f"Kinetic Layer: Executing precise click at ({x}, {y})")
                await self.page.mouse.move(x, y, steps=10)
                await self.page.mouse.click(x, y)
                return True
            except Exception as e:
                logger.error(f"Coordinate Click failed: {e}")
                return False
        return False

    async def scrape_search_results(self) -> List[Dict[str, str]]:
        """Fallback text-based scraper if visual grounding fails."""
        if not self.page: return []
        results = []
        try:
            elements = await self.page.query_selector_all('div.g, div.result')
            for el in elements[:5]:
                title_el = await el.query_selector('h3')
                link_el = await el.query_selector('a')
                if title_el and link_el:
                    results.append({
                        "title": await title_el.inner_text(),
                        "url": await link_el.get_attribute('href'),
                        "is_ad": "Sponsored" in (await el.inner_text())
                    })
            return results
        except Exception as e:
            logger.error(f"Scrape failed: {e}")
            return []

    async def find_and_click(self, selector: str, timeout: int = 10000):
        """Clicks elements using CSS selectors with automatic scroll-to-view."""
        try:
            await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            element = await self.page.query_selector(selector)
            await element.scroll_into_view_if_needed()
            await element.click()
            return True
        except Exception as e:
            logger.warning(f"Selector click failed for {selector}: {str(e)}")
            return False

    async def fill_field(self, selector: str, value: str):
        """Standard input filler with anti-bot typing delays."""
        try:
            await self.page.wait_for_selector(selector, state="visible", timeout=5000)
            await self.page.type(selector, value, delay=40)
            return True
        except Exception as e:
            logger.error(f"Field fill error: {str(e)}")
            return False

    async def get_screenshot_b64(self) -> str:
        """Captures viewport for Gemini 2.5 VLM coordinate mapping."""
        if not self.page: return ""
        
        if not os.path.exists(SCREENSHOT_PATH):
            os.makedirs(SCREENSHOT_PATH)

        path = os.path.join(SCREENSHOT_PATH, "current_view.png")
        # Snapshot must be of the viewport only to keep coordinate math accurate
        await self.page.screenshot(path=path, full_page=False)
        
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def close(self):
        """Clean shutdown of browser context and playwright engine."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.browser = None
        self.playwright = None
        logger.info("Browser resources released.")