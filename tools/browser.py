import asyncio
import base64
import os
import logging
import random
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import logger, SCREENSHOT_PATH, VIEWPORT_WIDTH, VIEWPORT_HEIGHT

class ArvynBrowser:
    """
    Advanced Kinetic Layer of Agent Arvyn (Production Grade).
    Features: 1080p Stealth Engine, Anti-detection fingerprinting, 
    and High-Res Visual Guarding.
    """
    
    def __init__(self, headless: bool = False):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = headless
        
        # Standardized viewport synchronized with Arvyn Config
        self.viewport_width = VIEWPORT_WIDTH
        self.viewport_height = VIEWPORT_HEIGHT

    async def start(self):
        """Initializes a hardened Chromium instance with 1080p resolution."""
        if self.browser:
            return

        self.playwright = await async_playwright().start()
        
        # Launching with stealth arguments to bypass advanced bot protection
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--start-maximized", 
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security"
            ]
        )
        
        # High-fidelity context for accurate VLM grounding
        self.context = await self.browser.new_context(
            viewport={'width': self.viewport_width, 'height': self.viewport_height},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            device_scale_factor=1,
            has_touch=True,
            is_mobile=False
        )
        
        # Cloak browser fingerprint
        await self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.page = await self.context.new_page()
        await self.page.goto("about:blank")
        
        logger.info(f"[BROWSER] Stealth engine active at {self.viewport_width}x{self.viewport_height}.")

    async def ensure_page(self) -> Page:
        """Ensures a valid page session is active."""
        if not self.page or self.page.is_closed():
            await self.start()
        return self.page

    async def navigate(self, url: str):
        """Navigates with recursive HTML verification to fix 'Blank Page' issues."""
        page = await self.ensure_page()
        try:
            logger.info(f"[NETWORK] Navigating to: {url}")
            
            # Using 'domcontentloaded' for speed with a manual buffer for hydration
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            if response and response.status >= 400:
                logger.warning(f"[WARNING] Server returned status: {response.status}")

            # Verification: Ensure the DOM is actually populated before handing over to the Brain
            for _ in range(15):
                content = await page.content()
                if len(content) > 1000: # Rio Bank page is substantial
                    break
                await asyncio.sleep(0.5)
            
            # Allow dynamic CSS/JS to settle
            await asyncio.sleep(2.5) 
            
        except Exception as e:
            logger.error(f"[ERROR] Navigation Failed: {e}")

    async def click_at_coordinates(self, x: int, y: int):
        """Human-like kinetic interaction with randomized movement paths."""
        page = await self.ensure_page()
        try:
            # Add jitter to bypass pixel-perfect bot traps
            target_x = x + random.randint(-1, 1)
            target_y = y + random.randint(-1, 1)
            
            # Simulated mouse movement trajectory
            await page.mouse.move(target_x, target_y, steps=random.randint(20, 30))
            await asyncio.sleep(random.uniform(0.1, 0.2))
            
            await page.mouse.down()
            await asyncio.sleep(random.uniform(0.05, 0.1))
            await page.mouse.up()
            
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Click failure at ({x}, {y}): {e}")
            return False

    async def type_text(self, text: str):
        """Simulates human typing rhythm with variable delays."""
        page = await self.ensure_page()
        try:
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.04, 0.14))
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Typing failure: {e}")
            return False

    async def get_dimensions(self) -> Dict[str, int]:
        """Returns the high-res viewport size."""
        page = await self.ensure_page()
        size = page.viewport_size
        return size if size else {"width": self.viewport_width, "height": self.viewport_height}

    async def get_screenshot_b64(self) -> str:
        """Resilient screenshot capture with increased timeout for heavy pages."""
        page = await self.ensure_page()
        
        if not os.path.exists(SCREENSHOT_PATH):
            os.makedirs(SCREENSHOT_PATH)

        path = os.path.join(SCREENSHOT_PATH, "current_view.png")
        
        try:
            # Fix for the 'Timeout 5000ms' error found in logs
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            logger.warning("[BROWSER] Network never went idle; taking screenshot anyway.")
        
        await page.screenshot(path=path, full_page=False)
        
        with open(path, "rb") as img:
            return base64.b64encode(img.read()).decode('utf-8')

    async def close(self):
        """Graceful release of all system resources."""
        if self.page: await self.page.close()
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
        
        self.browser = self.page = self.context = self.playwright = None
        logger.info("[BROWSER] Resources released.")