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
    UPGRADED: Features Human-Like Micro-Interactions, 1080p Precision Framing, 
    and Force-Registration clicking to resolve unresponsive UI elements.
    """
    
    def __init__(self, headless: bool = False):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = headless
        
        # Unified resolution from Config
        self.viewport_width = VIEWPORT_WIDTH
        self.viewport_height = VIEWPORT_HEIGHT

    async def start(self):
        """Initializes a hardened Chromium instance with forced 1080p window sizing."""
        if self.browser:
            return

        self.playwright = await async_playwright().start()
        
        # Force the window-size and device-scale to ensure 1:1 pixel mapping
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                f"--window-size={self.viewport_width},{self.viewport_height}",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--force-device-scale-factor=1" 
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': self.viewport_width, 'height': self.viewport_height},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            device_scale_factor=1,
            has_touch=True,
            is_mobile=False
        )
        
        await self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.page = await self.context.new_page()
        await self.page.set_viewport_size({"width": self.viewport_width, "height": self.viewport_height})
        await self.page.goto("about:blank")
        
        logger.info(f"[BROWSER] High-Precision Engine active at {self.viewport_width}x{self.viewport_height}.")

    async def ensure_page(self) -> Page:
        """Guarantees a valid page session is active."""
        if not self.page or self.page.is_closed():
            await self.start()
        return self.page

    async def navigate(self, url: str):
        """Navigates with recursive verification and hydration buffers."""
        page = await self.ensure_page()
        try:
            logger.info(f"[NETWORK] Connecting to: {url}")
            response = await page.goto(url, wait_until="networkidle", timeout=60000)
            
            if response and response.status >= 400:
                logger.warning(f"[WARNING] Navigation Alert: HTTP {response.status}")

            for _ in range(20):
                content = await page.content()
                if len(content) > 1500: 
                    break
                await asyncio.sleep(0.5)
            
            await asyncio.sleep(3.5) 
            
        except Exception as e:
            logger.error(f"[ERROR] Connection Failed: {e}")

    async def click_at_coordinates(self, x: int, y: int):
        """
        Superior Multi-Stage Physical Click.
        Simulates human movement, hover, and force-focused interaction 
        to ensure JS event listeners (like Rio Bank's) are triggered correctly.
        """
        page = await self.ensure_page()
        try:
            # 1. Micro-jitter for human realism
            target_x = x + random.uniform(-0.5, 0.5)
            target_y = y + random.uniform(-0.5, 0.5)
            
            logger.info(f"[KINETIC] Triggering Human-Like click at ({x}, {y})")
            
            # 2. Stage 1: Move mouse to target with 'momentum' (simulates hand movement)
            await page.mouse.move(target_x, target_y, steps=random.randint(25, 40))
            
            # 3. Stage 2: Hover to 'arm' event listeners
            await asyncio.sleep(random.uniform(0.2, 0.4))
            
            # 4. Stage 3: Perform actual down/up sequence with realistic 'dwell' time
            await page.mouse.down()
            await asyncio.sleep(random.uniform(0.1, 0.18))
            await page.mouse.up()
            
            # 5. Stage 4: Post-click focus stabilization
            await asyncio.sleep(0.5)
            
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Click failure at ({x}, {y}): {e}")
            return False

    async def type_text(self, text: str):
        """Human-like typing with variable cadence."""
        page = await self.ensure_page()
        try:
            logger.info("[KINETIC] Initiating keystroke sequence...")
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.18))
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Keystroke failure: {e}")
            return False

    async def get_dimensions(self) -> Dict[str, int]:
        """Returns the locked viewport dimensions."""
        page = await self.ensure_page()
        size = page.viewport_size
        return size if size else {"width": self.viewport_width, "height": self.viewport_height}

    async def get_screenshot_b64(self) -> str:
        """High-res capture with extended stabilization for Single Page Apps."""
        page = await self.ensure_page()
        
        if not os.path.exists(SCREENSHOT_PATH):
            os.makedirs(SCREENSHOT_PATH)

        path = os.path.join(SCREENSHOT_PATH, "current_view.png")
        
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except:
            pass 
        
        await page.screenshot(path=path, full_page=False)
        
        with open(path, "rb") as img:
            return base64.b64encode(img.read()).decode('utf-8')

    async def close(self):
        """Safe shutdown of all kinetic and networking layers."""
        if self.page: await self.page.close()
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
        
        self.browser = self.page = self.context = self.playwright = None
        logger.info("[BROWSER] Stealth engine deactivated.")