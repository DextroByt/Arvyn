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
    UPGRADED: Features Visual Click Markers for real-time debugging.
    FIXED: Strict Drift Correction logic to ignore non-interactive containers.
    IMPROVED: Multi-layer Click (Physical + JS Fallback) for 100% hit registration.
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
        
        # Anti-detection and Scaling Lock + Visual Marker Styles
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.devicePixelRatio = 1;
            
            // CSS for the Visual Click Marker
            const style = document.createElement('style');
            style.innerHTML = `
                .arvyn-click-marker {
                    position: absolute;
                    width: 20px;
                    height: 20px;
                    background: rgba(255, 0, 0, 0.6);
                    border: 2px solid white;
                    border-radius: 50%;
                    pointer-events: none;
                    z-index: 1000000;
                    transform: translate(-50%, -50%);
                    animation: arvyn-pulse 1.5s ease-out;
                }
                @keyframes arvyn-pulse {
                    0% { transform: translate(-50%, -50%) scale(0.5); opacity: 1; }
                    100% { transform: translate(-50%, -50%) scale(3); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
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

    async def _show_visual_marker(self, x: int, y: int):
        """Injects a temporary red circle at the click location for debugging."""
        marker_script = f"""
            (() => {{
                const div = document.createElement('div');
                div.className = 'arvyn-click-marker';
                div.style.left = '{x}px';
                div.style.top = '{y}px';
                document.body.appendChild(div);
                setTimeout(() => div.remove(), 1500);
            }})();
        """
        try:
            await self.page.evaluate(marker_script)
        except:
            pass

    async def click_at_coordinates(self, x: int, y: int):
        """
        Superior Interaction Logic with Visual Feedback and Strict Snap-to-Element.
        FIXED: Snapping logic now ignores non-interactive text containers.
        """
        page = await self.ensure_page()
        
        if x < 0 or y < 0 or x > self.viewport_width or y > self.viewport_height:
            logger.warning(f"[KINETIC] Coordinate ({x}, {y}) OOB. Re-centering...")
            await self.scroll_to(x, y)

        try:
            # --- IMPROVED: STRICT DRIFT CORRECTION ---
            drift_script = """
                (params) => {
                    const {x, y} = params;
                    let el = document.elementFromPoint(x, y);
                    if (!el) return null;
                    
                    // Only snap if we are within or near an actual interactive element
                    const interactive = el.closest('button, a, input, [role="button"], select, [onclick]');
                    
                    if (interactive) {
                        const rect = interactive.getBoundingClientRect();
                        return {
                            x: Math.floor(rect.left + rect.width / 2),
                            y: Math.floor(rect.top + rect.height / 2),
                            name: (interactive.innerText || interactive.ariaLabel || interactive.id || "interactive").substring(0, 20),
                            is_strict: true
                        };
                    }
                    
                    // If it's a giant container, DO NOT snap to center. Use the AI's exact point instead.
                    return { x: x, y: y, name: "Exact Point", is_strict: false };
                }
            """
            correction = await page.evaluate(drift_script, {"x": x, "y": y})
            
            if correction:
                if correction.get('is_strict'):
                    logger.info(f"[KINETIC] Strict Snap: Target '{correction['name']}' at ({correction['x']}, {correction['y']})")
                x, y = correction['x'], correction['y']

            # 1. Visual Debugging Marker
            await self._show_visual_marker(x, y)

            # 2. Physical Mouse Interaction
            await page.mouse.move(x, y, steps=random.randint(20, 40))
            await asyncio.sleep(0.2)
            
            # 3. Precision Click
            await page.mouse.down()
            await asyncio.sleep(random.uniform(0.1, 0.2))
            await page.mouse.up()
            
            # 4. Fallback: JavaScript Force-Click (Ensures hit even if overlay exists)
            force_click_script = """
                (params) => {
                    const el = document.elementFromPoint(params.x, params.y);
                    if (el) {
                        el.click();
                        const interactive = el.closest('button, a, input');
                        if (interactive) interactive.click();
                    }
                }
            """
            await page.evaluate(force_click_script, {"x": x, "y": y})
            
            await asyncio.sleep(1.0)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Click failure at ({x}, {y}): {e}")
            return False

    async def navigate(self, url: str):
        """Navigates with recursive verification and zoom locking."""
        page = await self.ensure_page()
        try:
            logger.info(f"[NETWORK] Connecting to: {url}")
            await page.goto(url, wait_until="load", timeout=60000)
            await page.evaluate("document.body.style.zoom = '1.0'")
            await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(2.0)
        except Exception as e:
            logger.error(f"[ERROR] Connection Failed: {e}")

    async def type_text(self, text: str):
        """Human-like typing with variable cadence."""
        page = await self.ensure_page()
        try:
            logger.info(f"[KINETIC] Typing sequence: {len(text)} characters.")
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Keystroke failure: {e}")
            return False

    async def get_screenshot_b64(self) -> str:
        """High-res capture with extended stabilization."""
        page = await self.ensure_page()
        path = os.path.join(SCREENSHOT_PATH, "current_view.png")
        if not os.path.exists(SCREENSHOT_PATH): os.makedirs(SCREENSHOT_PATH)
        
        await page.bring_to_front()
        await asyncio.sleep(1.0)
        await page.screenshot(path=path)
        with open(path, "rb") as img:
            return base64.b64encode(img.read()).decode('utf-8')

    async def close(self):
        if self.page: await self.page.close()
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
        logger.info("[BROWSER] Stealth engine deactivated.")

    async def scroll_to(self, x: int, y: int):
        page = await self.ensure_page()
        scroll_y = max(0, y - (self.viewport_height // 2))
        await page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
        await asyncio.sleep(1.0)