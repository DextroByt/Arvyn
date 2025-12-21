import asyncio
import logging
from tools.browser import ArvynBrowser
from config import logger

async def test_hidden_dom_sync():
    print("🚀 Starting Semantic Sync Verification (v5.0)...")
    browser = ArvynBrowser(headless=False)
    
    try:
        # 1. Initialize and Navigate
        await browser.start()
        target_url = "https://roshan-chaudhary13.github.io/rio_finance_bank/"
        await browser.navigate(target_url)
        
        # 2. Define a target (e.g., the 'Login' or 'Gold' button)
        # We will use the "Electricity Bill" link as an example
        element_label = "Electricity" 
        
        # 3. Simulate "VLM Drift"
        # We provide coordinates that are purposely 100px away from the actual button
        # On a 1920x1080 screen, let's assume the button is at (500, 500)
        # We tell the engine to click at (600, 600)
        vlm_proposed_x = 600
        vlm_proposed_y = 600
        
        print(f"DEBUG: VLM proposing DRIFTED coordinates: ({vlm_proposed_x}, {vlm_proposed_y})")
        print(f"DEBUG: Semantic Hint provided: '{element_label}'")
        
        # 4. Execute Click with Hint
        # The 'element_hint' triggers the _perform_stealth_dom_sync logic
        success = await browser.click_at_coordinates(
            vlm_proposed_x, 
            vlm_proposed_y, 
            element_hint=element_label
        )
        
        if success:
            print("✅ SUCCESS: The Kinetic Layer anchored to the DOM element despite coordinate drift.")
        else:
            print("❌ FAILURE: Interaction failed.")
            
        # Keep open for 5 seconds to observe the visual crosshair
        await asyncio.sleep(5)

    except Exception as e:
        print(f"❌ ERROR during test: {e}")
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_hidden_dom_sync())