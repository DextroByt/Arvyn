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
    UPGRADED: Features Kinetic Drift Correction to resolve 100% scaling click errors.
    IMPROVED: Scaling-Locked Viewport to ensure coordinate precision across DPI settings.
    FIXED: Snap-to-Center logic for hit registration on the Login Button.
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
        """Initializes a hardened Chromium instance with scale-invariant window sizing."""
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
                # FIXED: Force the device scale factor to 1 to ignore OS-level scaling (100%/125%/etc)
                "--force-device-scale-factor=1",
                "--high-dpi-support=1",
                "--force-color-profile=srgb"
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': self.viewport_width, 'height': self.viewport_height},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            device_scale_factor=1,
            has_touch=True,
            is_mobile=False
        )
        
        # Anti-detection and Scaling Lock
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.devicePixelRatio = 1;
        """)
        
        self.page = await self.context.new_page()
        await self.page.set_viewport_size({"width": self.viewport_width, "height": self.viewport_height})
        await self.page.goto("about:blank")
        
        logger.info(f"[BROWSER] Scale-Invariant Engine active at {self.viewport_width}x{self.viewport_height}.")

    async def ensure_page(self) -> Page:
        """Guarantees a valid page session is active."""
        if not self.page or self.page.is_closed():
            await self.start()
        return self.page

    async def navigate(self, url: str):
        """Navigates with recursive verification and zoom locking."""
        page = await self.ensure_page()
        try:
            logger.info(f"[NETWORK] Connecting to: {url}")
            response = await page.goto(url, wait_until="load", timeout=90000)
            
            # IMPROVEMENT: Force internal zoom to 100% to fix coordinate drift on Home screens
            await page.evaluate("document.body.style.zoom = '1.0'")
            
            if response and response.status >= 400:
                logger.warning(f"[WARNING] Navigation Alert: HTTP {response.status}")

            for _ in range(30):
                content = await page.content()
                if len(content) > 2500: 
                    break
                await asyncio.sleep(0.5)
            
            await page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(2.5) 
            
        except Exception as e:
            logger.error(f"[ERROR] Connection Failed: {e}")

    async def scroll_to(self, x: int, y: int):
        """Physically scrolls the viewport to ensure the target is visible."""
        page = await self.ensure_page()
        try:
            scroll_y = max(0, y - (self.viewport_height // 2))
            await page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
            await asyncio.sleep(1.8)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Scroll failure: {e}")
            return False

    async def click_at_coordinates(self, x: int, y: int):
        """
        Superior Cluster-Click Interaction with Kinetic Drift Correction.
        FIXED: Uses document.elementFromPoint to resolve coordinate mismatches at 100% scale.
        """
        page = await self.ensure_page()
        
        if x < 0 or y < 0 or x > self.viewport_width or y > self.viewport_height:
            logger.warning(f"[KINETIC] Coordinate ({x}, {y}) OOB. Re-centering...")
            await self.scroll_to(x, y)

        try:
            # --- IMPROVEMENT: KINETIC DRIFT CORRECTION ---
            # Query the DOM for the actual element at the coordinates provided by the AI.
            # This ensures we click the center of the Login button even if the coordinates are slightly off.
            drift_script = """
                (x, y) => {
                    const el = document.elementFromPoint(x, y);
                    if (!el) return null;
                    const rect = el.getBoundingClientRect();
                    return {
                        x: Math.floor(rect.left + rect.width / 2),
                        y: Math.floor(rect.top + rect.height / 2),
                        name: el.innerText || el.ariaLabel || el.id
                    };
                }
            """
            correction = await page.evaluate(drift_script, x, y)
            
            if correction and correction['x'] > 0:
                logger.info(f"[KINETIC] Drift Correction: Snapping to center of '{correction['name']}' at ({correction['x']}, {correction['y']})")
                x, y = correction['x'], correction['y']

            # Stage 1: Move mouse to target
            await page.mouse.move(x, y, steps=random.randint(30, 50))
            await asyncio.sleep(0.3)
            
            # Stage 2: Cluster Click Pattern
            click_pattern = [(0, 0), (1, 1), (-1, -1)]
            for ox, oy in click_pattern:
                tx, ty = x + ox, y + oy
                await page.mouse.move(tx, ty, steps=3)
                await page.mouse.down()
                await asyncio.sleep(random.uniform(0.1, 0.2))
                await page.mouse.up()
                await asyncio.sleep(0.05)
            
            await asyncio.sleep(1.2)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Click failure at ({x}, {y}): {e}")
            return False

    async def type_text(self, text: str):
        """Human-like typing with variable cadence."""
        page = await self.ensure_page()
        try:
            logger.info(f"[KINETIC] Typing sequence: {len(text)} characters.")
            for char in text:
                await page.keyboard.type(char)
                delay = random.uniform(0.08, 0.18) if char.isalnum() else random.uniform(0.2, 0.4)
                await asyncio.sleep(delay)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Keystroke failure: {e}")
            return False

    async def press_key(self, key: str):
        """Simulates a physical key press."""
        page = await self.ensure_page()
        try:
            logger.info(f"[KINETIC] Pressing system key: {key}")
            await page.keyboard.press(key)
            await asyncio.sleep(1.0)
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
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(1.5)
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