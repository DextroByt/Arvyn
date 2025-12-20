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
    UPGRADED: Features Cluster-Click Engine for high-precision hit registration.
    IMPROVED: Enhanced state-stabilization and human-like rhythmic typing.
    """
    
    def __init__(self, headless: bool = False):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = headless
        self.viewport_width = VIEWPORT_WIDTH
        self.viewport_height = VIEWPORT_HEIGHT

    async def start(self):
        """Initializes a hardened Chromium instance with forced 1080p window sizing."""
        if self.browser:
            return

        self.playwright = await async_playwright().start()
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

    async def scroll_to(self, x: int, y: int):
        """Physically scrolls the viewport to ensure the target is visible."""
        page = await self.ensure_page()
        try:
            scroll_y = max(0, y - (self.viewport_height // 3))
            await page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
            await asyncio.sleep(1.5)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Scroll failure: {e}")
            return False

    async def click_at_coordinates(self, x: int, y: int):
        """
        Superior Cluster-Click Interaction.
        Instead of one click, it performs a 3-point micro-pattern to ensure 
        the UI element registers the 'click' event even if it has a small hit-box.
        """
        page = await self.ensure_page()
        
        if x < 0 or y < 0 or x > self.viewport_width or y > self.viewport_height:
            logger.warning(f"[KINETIC] Coordinate ({x}, {y}) OOB. Scrolling...")
            await self.scroll_to(x, y)

        try:
            # Stage 1: Move mouse to target with momentum
            await page.mouse.move(x, y, steps=random.randint(25, 40))
            await asyncio.sleep(0.3)
            
            # Stage 2: Perform 'Cluster Click' (Primary + 2 Diamond Offsets)
            # This ensures responsiveness on complex banking portals
            click_pattern = [(0, 0), (2, 2), (-2, -2)]
            
            logger.info(f"[KINETIC] Executing Cluster-Click sequence at central point ({x}, {y})")
            
            for ox, oy in click_pattern:
                tx, ty = x + ox, y + oy
                await page.mouse.move(tx, ty, steps=5)
                await page.mouse.down()
                await asyncio.sleep(random.uniform(0.1, 0.2))
                await page.mouse.up()
                await asyncio.sleep(0.05) # Rapid sequence
            
            # Stage 3: Stabilization wait for UI transition
            await asyncio.sleep(1.2)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Click failure at ({x}, {y}): {e}")
            return False

    async def type_text(self, text: str):
        """Human-like typing with variable cadence and rhythmic delay."""
        page = await self.ensure_page()
        try:
            logger.info(f"[KINETIC] Typing sequence: {len(text)} characters.")
            for char in text:
                # Mimic human rhythmic typing (fast-slow-fast)
                await page.keyboard.type(char)
                delay = random.uniform(0.05, 0.15) if char.isalnum() else random.uniform(0.15, 0.3)
                await asyncio.sleep(delay)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Keystroke failure: {e}")
            return False

    async def press_key(self, key: str):
        """Simulates a physical key press (e.g. 'Enter', 'Tab')."""
        page = await self.ensure_page()
        try:
            logger.info(f"[KINETIC] Pressing system key: {key}")
            await page.keyboard.press(key)
            await asyncio.sleep(0.8)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Key press error: {e}")
            return False

    async def get_dimensions(self) -> Dict[str, int]:
        """Returns the locked viewport dimensions."""
        page = await self.ensure_page()
        size = page.viewport_size
        return size if size else {"width": self.viewport_width, "height": self.viewport_height}

    async def get_screenshot_b64(self) -> str:
        """High-res capture with extended stabilization."""
        page = await self.ensure_page()
        if not os.path.exists(SCREENSHOT_PATH):
            os.makedirs(SCREENSHOT_PATH)

        path = os.path.join(SCREENSHOT_PATH, "current_view.png")
        try:
            await page.bring_to_front()
            await page.wait_for_load_state("networkidle", timeout=15000)
            # Extra wait to ensure CSS transitions/loaders finish
            await asyncio.sleep(1.0)
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