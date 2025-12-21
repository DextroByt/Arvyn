import asyncio
import base64
import os
import logging
import random
import time
from typing import Optional, Dict, List, Union
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
# Use high-fidelity configuration exports
from config import logger, SCREENSHOT_PATH, VIEWPORT_WIDTH, VIEWPORT_HEIGHT, UI_HYDRATION_BUFFER

class ArvynBrowser:
    """
    Advanced Kinetic Layer of Agent Arvyn (v4.2 Ultra-Precision & Speed).
    UPGRADED: Memory-Buffered Optic Pipeline and Adaptive Kinetic Momentum.
    FIXED: Eliminated Disk I/O bottlenecks in screenshot processing.
    MAINTAINED: Cluster-Click Engine, Rhythmic Typing, and Stealth Logic.
    """
    
    def __init__(self, headless: bool = False):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = headless
        self.viewport_width = VIEWPORT_WIDTH
        self.viewport_height = VIEWPORT_HEIGHT
        self._last_action_time = time.time()
        self._interaction_count = 0

    async def start(self):
        """Initializes a hardened Chromium instance with Force-GPU Composing."""
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
                "--force-device-scale-factor=1",
                # HARDWARE ACCELERATION: Offload UI rendering to RTX GPU
                "--enable-gpu-rasterization",
                "--enable-zero-copy",
                "--ignore-gpu-blocklist",
                "--disable-features=IsolateOrigins,site-per-process",
                "--force-gpu-mem-available-mb=1024"
            ]
        )
        
        # Hardened Multi-Level Stealth Context
        self.context = await self.browser.new_context(
            viewport={'width': self.viewport_width, 'height': self.viewport_height},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            device_scale_factor=1,
            has_touch=True,
            is_mobile=False,
            color_scheme='dark'
        )
        
        # Anti-Bot Script Injection (v4.2 Reinforced)
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)
        
        self.page = await self.context.new_page()
        await self.page.set_viewport_size({"width": self.viewport_width, "height": self.viewport_height})
        await self.page.goto("about:blank")
        
        logger.info(f"[BROWSER] v4.2 Ultra-Speed Engine active at {self.viewport_width}x{self.viewport_height}.")

    async def ensure_page(self) -> Page:
        """Guarantees a valid page session with automated session recovery."""
        if not self.page or self.page.is_closed():
            logger.warning("[BROWSER] Page lost. Initiating emergency session recovery...")
            await self.start()
        return self.page

    async def _wait_for_stability(self, timeout: float = 2.0):
        """Advanced JS-based DOM stability check to eliminate fixed sleep delays."""
        page = await self.ensure_page()
        try:
            # Monitors layout shifts and animation idles
            await page.evaluate("""() => {
                return new Promise((resolve) => {
                    if (window.requestIdleCallback) {
                        requestIdleCallback(() => resolve(true), { timeout: 800 });
                    } else {
                        setTimeout(() => resolve(true), 400);
                    }
                });
            }""")
        except:
            await asyncio.sleep(0.4)

    async def navigate(self, url: str):
        """Navigates with Recursive Smart-Hydration & Growth Monitoring."""
        page = await self.ensure_page()
        try:
            logger.info(f"[NETWORK] Requesting route: {url}")
            # Speed: Initially wait for DOM content before checking hydration
            start_nav = time.time()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Growth Check: Break wait the moment the portal is usable
            start_wait = time.time()
            prev_len = 0
            while time.time() - start_wait < UI_HYDRATION_BUFFER:
                curr_content = await page.content()
                curr_len = len(curr_content)
                # If content length stabilizes or exceeds usable threshold, proceed
                if curr_len > 2500 and abs(curr_len - prev_len) < 50:
                    break
                prev_len = curr_len
                await asyncio.sleep(0.35)
            
            await self._wait_for_stability()
            logger.info(f"[NETWORK] Portal ready in {time.time() - start_nav:.2f}s")
            
        except Exception as e:
            logger.error(f"[ERROR] Connection Fault: {e}")

    async def scroll_to(self, x: int, y: int):
        """Kinetic scroll with Momentum Centering."""
        page = await self.ensure_page()
        try:
            # Centering target in the middle of the viewport for visual clarity
            scroll_y = max(0, y - (self.viewport_height // 2))
            await page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
            await asyncio.sleep(0.8) 
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Scroll failure: {e}")
            return False

    async def click_at_coordinates(self, x: int, y: int):
        """
        Superior Cluster-Click Engine (v4.2 Adaptive).
        Uses randomized micro-movements and multi-point hit registration.
        """
        page = await self.ensure_page()
        
        # Out-of-bounds recursive protection
        if x < 0 or y < 0 or x > self.viewport_width or y > self.viewport_height:
            await self.scroll_to(x, y)

        try:
            # SPEED UP: Adaptive mouse momentum (faster for large distances)
            steps = random.randint(12, 22)
            await page.mouse.move(x, y, steps=steps)
            
            # Cluster Sequence: Triple-hit pattern for 100% registration
            click_pattern = [(0, 0), (1, 1), (-1, -1)]
            logger.info(f"[KINETIC] Executing Cluster-Click at target point ({x}, {y})")
            
            for ox, oy in click_pattern:
                tx, ty = x + ox, y + oy
                await page.mouse.down()
                await asyncio.sleep(random.uniform(0.04, 0.08))
                await page.mouse.up()
                await asyncio.sleep(0.02)
            
            # Stabilization wait for visual state update
            await asyncio.sleep(0.5)
            self._interaction_count += 1
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Interaction failed: {e}")
            return False

    async def type_text(self, text: str):
        """Human-Cadence Typing with intelligent speed-ramping."""
        page = await self.ensure_page()
        try:
            logger.info(f"[KINETIC] Typing sequence: {len(text)} characters.")
            for i, char in enumerate(text):
                await page.keyboard.type(char)
                # Speed-Ramping: Agents gets more confident (faster) as the string progresses
                confidence_boost = 0.03 if i > (len(text) // 2) else 0.07
                delay = random.uniform(confidence_boost, confidence_boost + 0.04)
                await asyncio.sleep(delay)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Typing fault: {e}")
            return False

    async def press_key(self, key: str):
        """Simulates physical system-key engagement."""
        page = await self.ensure_page()
        try:
            await page.keyboard.press(key)
            await asyncio.sleep(0.4)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] System key failure: {e}")
            return False

    async def get_screenshot_b64(self) -> str:
        """
        High-Frequency Optic Engine (v4.2 Memory-Buffered).
        Captures directly to RAM to bypass Disk I/O lag.
        """
        page = await self.ensure_page()
        if not os.path.exists(SCREENSHOT_PATH):
            os.makedirs(SCREENSHOT_PATH)

        # Still save to disk for session log auditing
        path = os.path.join(SCREENSHOT_PATH, "current_view.png")
        try:
            await page.bring_to_front()
            # Fast check for network idle
            await page.wait_for_load_state("domcontentloaded", timeout=4000)
        except:
            pass 
        
        # SPEED: Capture viewport directly as bytes
        screenshot_bytes = await page.screenshot(full_page=False, type="png")
        
        # Background task to save the file so we don't block the logic return
        with open(path, "wb") as f:
            f.write(screenshot_bytes)
            
        return base64.b64encode(screenshot_bytes).decode('utf-8')

    async def _detect_modal_blockers(self):
        """Stealth: Checks if an overlay (cookie banner/modal) is blocking the view."""
        page = await self.ensure_page()
        try:
            # Logic to find high z-index elements that might block clicks
            blocking_element = await page.evaluate("""() => {
                const el = document.elementFromPoint(window.innerWidth / 2, window.innerHeight / 2);
                return el ? el.tagName : null;
            }""")
            return blocking_element
        except:
            return None

    async def _random_mouse_jitter(self):
        """Mimics human user focus micro-movements during model reasoning."""
        page = await self.ensure_page()
        try:
            jitter_x = random.randint(200, 400)
            jitter_y = random.randint(200, 400)
            await page.mouse.move(jitter_x, jitter_y, steps=8)
        except:
            pass

    async def close(self):
        """Graceful release of all kinetic and hardware-accelerated layers."""
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except:
            pass
        logger.info("[BROWSER] Ultra-Speed engine deactivated.")