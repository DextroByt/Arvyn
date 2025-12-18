import asyncio
import base64
import logging
from typing import Dict, Optional, Any
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, ElementHandle

from config import HEADLESS_MODE, USER_AGENT, BROWSER_TIMEOUT, logger

class BrowserManager:
    """
    The 'Hands' of Agent Arvyn.
    Manages the Playwright browser instance, page interactions, and state capture.
    """
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_running = False

    async def start(self):
        """Initializes the browser session with anti-detection headers."""
        if self.is_running:
            return

        logger.info("Initializing Playwright Browser...")
        self.playwright = await async_playwright().start()
        
        # Launch options for better stability
        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS_MODE,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized" 
            ]
        )
        
        self.context = await self.browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080}, # Standard desktop resolution
            record_video_dir="logs/videos/" if not HEADLESS_MODE else None # Record debug video
        )
        
        self.page = await self.context.new_page()
        self.is_running = True
        logger.info("Browser started successfully.")

    async def stop(self):
        """Clean shutdown."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.is_running = False
        logger.info("Browser stopped.")

    async def execute_action(self, action_type: str, selector: str = None, value: str = None):
        """
        Executes a single atomic action on the current page.
        """
        if not self.page:
            raise RuntimeError("Browser not started!")

        logger.debug(f"Executing Action: {action_type} on {selector}")

        try:
            if action_type == "NAVIGATE":
                await self.page.goto(value, timeout=BROWSER_TIMEOUT)
                await self.page.wait_for_load_state("networkidle")
            
            elif action_type == "CLICK":
                await self._highlight_element(selector)
                await self.page.click(selector, timeout=5000)
            
            elif action_type == "INPUT":
                await self._highlight_element(selector)
                await self.page.fill(selector, value)
            
            elif action_type == "SCROLL":
                await self.page.evaluate("window.scrollBy(0, 500)")
            
            elif action_type == "WAIT":
                await asyncio.sleep(2)
                
            elif action_type == "DONE":
                logger.info("Task marked as complete by Agent.")
                
            else:
                logger.warning(f"Unknown action type: {action_type}")

        except Exception as e:
            logger.error(f"Action Failed ({action_type}): {e}")
            raise e # Propagate to Orchestrator for handling

    async def click_at_coordinates(self, x_norm: float, y_norm: float):
        """
        Visual Grounding: Clicks at specific percentage coordinates (0.0-1.0).
        Used when CSS selectors fail.
        """
        if not self.page: 
            return
            
        viewport = self.page.viewport_size
        if not viewport:
            viewport = {"width": 1920, "height": 1080}
            
        abs_x = x_norm * viewport["width"]
        abs_y = y_norm * viewport["height"]
        
        logger.info(f"Visual Click at: {abs_x}, {abs_y}")
        
        # Draw a temporary visual marker
        await self.page.evaluate(f"""
            const dot = document.createElement('div');
            dot.style.position = 'fixed';
            dot.style.left = '{abs_x}px';
            dot.style.top = '{abs_y}px';
            dot.style.width = '20px';
            dot.style.height = '20px';
            dot.style.backgroundColor = 'red';
            dot.style.borderRadius = '50%';
            dot.style.zIndex = '99999';
            document.body.appendChild(dot);
            setTimeout(() => dot.remove(), 1000);
        """)
        
        await self.page.mouse.click(abs_x, abs_y)

    async def get_state(self) -> Dict[str, Any]:
        """
        Captures the current state of the page (URL + Screenshot) for the AI Brain.
        """
        if not self.page:
            return {"url": "No Browser", "screenshot": None}

        screenshot_bytes = await self.page.screenshot(type="png")
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        
        return {
            "url": self.page.url,
            "screenshot": screenshot_b64
        }

    async def _highlight_element(self, selector: str):
        """
        Visual UX: Draws a red border around the element before interacting.
        Helps user see what the AI is doing.
        """
        try:
            loc = self.page.locator(selector).first
            await loc.evaluate("el => el.style.border = '4px solid #FF0000'")
            await asyncio.sleep(0.5) # Slight pause so user can see it
            await loc.evaluate("el => el.style.border = ''")
        except Exception:
            pass # Ignore highlighting errors if element is weird