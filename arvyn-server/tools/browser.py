import asyncio
import logging
import sys
import platform
import traceback

# --- ADVANCED DEBUGGING: PRE-IMPORT CHECKS ---
# Check if sync_api is somehow already loaded by another module
if "playwright.sync_api" in sys.modules:
    print("⚠️ WARNING: 'playwright.sync_api' is loaded in sys.modules! This may cause conflicts.")

from playwright.async_api import async_playwright, Playwright, BrowserContext, Error as PlaywrightError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:     %(message)s')
logger = logging.getLogger(__name__)

# --- Classes required by main.py ---
class ConnectionError(Exception):
    """Custom exception for connection failures."""
    pass

class PageContextPlaceholder:
    """Placeholder class for when page context is unavailable."""
    pass
# ------------------------------------

class BrowserService:
    def __init__(self, cdp_url: str):
        self.cdp_url = cdp_url
        self.playwright: Playwright = None
        self.browser: BrowserContext = None
        
        # --- ADVANCED DEBUGGING: WINDOWS FIX ---
        # On Windows, the default ProactorEventLoop can conflict with Playwright's drivers.
        # We enforce SelectorEventLoopPolicy if not already running.
        if platform.system() == 'Windows':
            try:
                policy = asyncio.get_event_loop_policy()
                if "ProactorEventLoopPolicy" in str(type(policy)):
                    logger.info("🔧 Advanced Fix: Detected Windows ProactorLoop. Switching to SelectorEventLoopPolicy for Playwright compatibility.")
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except Exception as e:
                logger.warning(f"⚠️ Could not apply Windows Loop Policy fix: {e}")

    async def start(self):
        """Initializes the Playwright Async engine."""
        try:
            logger.info("Starting Playwright Async Engine...")
            self.playwright = await async_playwright().start()
            
            # Sanity check to ensure we got the Async engine
            mw_type = str(type(self.playwright))
            if "AsyncPlaywright" not in mw_type:
                logger.critical(f"❌ FATAL: Playwright initialized as {mw_type}. Expected AsyncPlaywright!")
                raise RuntimeError(f"Wrong Playwright Type: {mw_type}")
            
            logger.info(f"✅ Engine Started. Type: {mw_type}")
            
        except Exception as e:
            logger.error(f"❌ Engine Start Failed: {traceback.format_exc()}")
            raise

    async def connect(self):
        """
        Connects to an existing Chrome instance via CDP asynchronously.
        """
        if not self.playwright:
            await self.start()

        try:
            logger.info(f"🔗 Connecting to Chrome at: {self.cdp_url}")
            
            # --- ADVANCED DEBUGGING: INTERNAL CHECK ---
            # Verify we are in a running loop
            try:
                loop = asyncio.get_running_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed!")
            except RuntimeError:
                logger.error("❌ No running event loop detected during connect!")
                return False

            # ATTENTION: This is the critical line.
            # We explicitly await the connection.
            self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
            
            logger.info("✅ Browser Connected Successfully via Async API")
            return True
            
        except PlaywrightError as pe:
            # This captures the specific "Sync API inside Asyncio" error
            logger.error(f"❌ Playwright Internal Error: {pe}")
            logger.error(f"🕵️ Traceback: {traceback.format_exc()}")
            
            if "Sync API" in str(pe):
                logger.critical("🚨 CRITICAL: The environment is triggering the Sync API guard.")
                logger.critical("   1. Ensure NO 'from playwright.sync_api' exists in your entire project.")
                logger.critical("   2. Ensure you are not running this inside a thread that has a loop attached.")
            return False
            
        except Exception as e:
            logger.error(f"❌ General Connection Error: {e}")
            logger.error(f"🕵️ Traceback: {traceback.format_exc()}")
            return False

    async def execute_transfer_command(self, recipient: str, amount: int):
        """
        Simulates the banking task.
        """
        if not self.browser:
            logger.error("Browser not connected. Cannot execute command.")
            return

        try:
            # Get the active context (or create a new page)
            context = self.browser.contexts[0] if self.browser.contexts else self.browser
            
            # If no pages exist, create one; otherwise use the first one
            if context.pages:
                page = context.pages[0]
                logger.info("📄 Attached to existing tab.")
            else:
                page = await context.new_page()
                logger.info("📄 Created new tab.")

            logger.info(f"🤖 Agent Action: Navigating to Banking Portal...")
            
            # --- AUTOMATION LOGIC (ALL AWAITED) ---
            # await page.goto("https://bank.example.com")
            # await page.locator("#recipient").fill(recipient)
            
            await asyncio.sleep(1) 
            logger.info(f"📝 Filling form: Transfer ${amount} to {recipient}")
            
            await asyncio.sleep(1)
            logger.info("👉 Clicking 'Submit'")
            
            logger.info("✅ Transfer Complete.")
        except Exception as e:
            logger.error(f"❌ Automation Error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def stop(self):
        """Cleanup resources."""
        logger.info("🛑 Stopping Playwright Service...")
        if self.browser:
            try:
                await self.browser.close()
                logger.info("   - Browser disconnected")
            except Exception as e:
                logger.warning(f"   - Error closing browser: {e}")
                
        if self.playwright:
            try:
                await self.playwright.stop()
                logger.info("   - Playwright engine stopped")
            except Exception as e:
                logger.warning(f"   - Error stopping playwright: {e}")

# --- SIMULATED SERVER HANDLER ---
async def handle_command_request(command_data: dict, browser_service: BrowserService):
    logger.info(f"🎤 New Command: {command_data['text']}")
    
    if "Transfer" in command_data['text']:
        await browser_service.execute_transfer_command(
            recipient="Jane Doe", 
            amount=150
        )

# --- MAIN ASYNCIO LOOP ---
async def main():
    # 1. Configuration
    CDP_ENDPOINT = "http://127.0.0.1:9222" 
    
    # 2. Initialize Service
    service = BrowserService(CDP_ENDPOINT)
    
    try:
        # Note: connect() now handles start() if needed
        await service.start()

        # 3. Attempt Connection
        connected = await service.connect()

        if connected:
            # 4. Simulate receiving the HTTP POST request
            mock_payload = {
                "session": "cd5b3972-4096-4fb3",
                "text": "Transfer one hundred fifty dollars to Jane Doe, this is critical."
            }
            await handle_command_request(mock_payload, service)
    finally:
        # 5. Cleanup
        await service.stop()

if __name__ == "__main__":
    # Standard asyncio run
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass