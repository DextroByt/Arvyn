import asyncio
import base64
import os
import logging
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import logger, SCREENSHOT_PATH

class ArvynBrowser:
    """
    Advanced Kinetic Layer of Agent Arvyn (Production Grade).
    Fixed: Guaranteed page initialization to prevent 'NoneType' attribute errors 
    and support for dynamic viewport scaling across different laptop resolutions.
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
        
        # Consistent context for Gemini's vision
        self.context = await self.browser.new_context(
            viewport={'width': self.viewport_width, 'height': self.viewport_height},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        self.page = await self.context.new_page()
        
        # CRITICAL FIX: Initialize with a blank state so 'keyboard' and 'mouse' exist immediately
        await self.page.goto("about:blank")
        
        logger.info(f"Intelligent Browser Engine started and initialized at {self.viewport_width}x{self.viewport_height}.")

    async def ensure_page(self):
        """Safety check to ensure the page object is alive before any kinetic action."""
        if not self.page:
            await self.start()
        return self.page

    async def get_dimensions(self) -> Dict[str, int]:
        """Dynamically retrieves the actual current viewport size for coordinate mapping."""
        page = await self.ensure_page()
        size = page.viewport_size
        return size if size else {"width": self.viewport_width, "height": self.viewport_height}

    async def navigate(self, url: str):
        """Navigates with a safety buffer and guaranteed initialization."""
        await self.ensure_page()
        try:
            logger.info(f"Navigating to {url}...")
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1) 
        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")

    async def click_at_coordinates(self, x: int, y: int):
        """Executes a precise mouse click at calculated (x, y) pixels."""
        page = await self.ensure_page()
        try:
            logger.info(f"Kinetic Layer: Executing precise click at ({x}, {y})")
            await page.mouse.move(x, y, steps=10)
            await page.mouse.click(x, y)
            return True
        except Exception as e:
            logger.error(f"Coordinate Click failed: {e}")
            return False

    async def type_text(self, text: str, delay: int = 50):
        """Advanced keyboard interaction with initialization safety."""
        page = await self.ensure_page()
        try:
            logger.info(f"Kinetic Layer: Typing sequence initiated.")
            await page.keyboard.type(text, delay=delay)
            return True
        except Exception as e:
            logger.error(f"Typing sequence failed: {e}")
            return False

    async def scrape_search_results(self) -> List[Dict[str, str]]:
        """Fallback text-based scraper."""
        page = await self.ensure_page()
        results = []
        try:
            elements = await page.query_selector_all('div.g, div.result')
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
        page = await self.ensure_page()
        try:
            await page.wait_for_selector(selector, state="visible", timeout=timeout)
            element = await page.query_selector(selector)
            await element.scroll_into_view_if_needed()
            await element.click()
            return True
        except Exception as e:
            logger.warning(f"Selector click failed for {selector}: {str(e)}")
            return False

    async def fill_field(self, selector: str, value: str):
        """Standard input filler with anti-bot typing delays."""
        page = await self.ensure_page()
        try:
            await page.wait_for_selector(selector, state="visible", timeout=5000)
            await page.type(selector, value, delay=40)
            return True
        except Exception as e:
            logger.error(f"Field fill error: {str(e)}")
            return False

    async def get_screenshot_b64(self) -> str:
        """Captures viewport for Gemini 2.5 VLM coordinate mapping."""
        page = await self.ensure_page()
        
        if not os.path.exists(SCREENSHOT_PATH):
            os.makedirs(SCREENSHOT_PATH)

        path = os.path.join(SCREENSHOT_PATH, "current_view.png")
        await page.screenshot(path=path, full_page=False)
        
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