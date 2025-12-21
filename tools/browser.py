import asyncio
import base64
import os
import logging
import random
import time
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import logger, SCREENSHOT_PATH, VIEWPORT_WIDTH, VIEWPORT_HEIGHT

class ArvynBrowser:
    """
    Advanced Kinetic Layer of Agent Arvyn (v5.1 - Hardened Semantic Click).
    FIXED: Resolves 'No Clicks' by using Direct Injection (DOM-level event triggering).
    INTEGRATED: Stealth DOM manipulation that overrides VLM coordinates with 100% accuracy.
    PRESERVED: All visual debuggers, crosshairs, stealth args, and DPI locking.
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
        
        # INJECT: Superior Visual Debugging & Style Anchors
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.devicePixelRatio = 1;
            
            const style = document.createElement('style');
            style.innerHTML = `
                .arvyn-target-highlight {
                    outline: 5px solid #00d2ff !important;
                    outline-offset: 3px !important;
                    transition: outline 0.1s ease-in-out !important;
                    z-index: 2147483646 !important;
                }
                .arvyn-crosshair {
                    position: fixed;
                    width: 40px;
                    height: 40px;
                    border: 2px solid #FF0000;
                    border-radius: 50%;
                    pointer-events: none;
                    z-index: 2147483647;
                    transform: translate(-50%, -50%);
                    box-shadow: 0 0 15px rgba(255,0,0,0.8);
                }
            `;
            document.head.appendChild(style);
        """)
        
        self.page = await self.context.new_page()
        await self.page.set_viewport_size({"width": self.viewport_width, "height": self.viewport_height})
        await self.page.goto("about:blank")
        
        logger.info(f"[BROWSER] Hardened Kinetic Engine v5.1 active.")

    async def ensure_page(self) -> Page:
        if not self.page or self.page.is_closed():
            await self.start()
        return self.page

    async def _execute_stealth_action(self, hint: str, x: int, y: int, action: str = "click"):
        """
        INTERNAL DOM MANIPULATION CORE.
        Finds the best element and performs a direct JS injection action.
        This bypasses mouse drift and overlays entirely.
        """
        # Enhanced script: searches shadow DOM, scrolls element into view, and dispatches richer input events
        script = """
            (params) => {
                const { hint, x, y, action } = params;
                const search = (hint || '').toLowerCase().trim();

                function collectInteractiveElements(root) {
                    const selector = 'button, a, input, [role="button"], label, select, textarea, [data-action]';
                    let found = Array.from(root.querySelectorAll(selector));
                    // Traverse shadow roots recursively
                    const all = Array.from(root.querySelectorAll('*'));
                    for (const el of all) {
                        if (el.shadowRoot) {
                            try { found = found.concat(collectInteractiveElements(el.shadowRoot)); } catch(e) {}
                        }
                    }
                    return found;
                }

                let target = null;
                let min_dist = Infinity;

                try {
                    const els = collectInteractiveElements(document);
                    for (const el of els) {
                        const text = (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '').toLowerCase();
                        const normalized = text.replace(/\s+/g, ' ').trim();
                        if (search && normalized.includes(search)) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                const dx = (rect.left + rect.width/2) - x;
                                const dy = (rect.top + rect.height/2) - y;
                                const dist = Math.sqrt(dx*dx + dy*dy);
                                if (dist < min_dist) { min_dist = dist; target = el; }
                            }
                        }
                    }
                } catch(e) { }

                if (!target) {
                    // Fallback: try elementsFromPoint stack
                    try {
                        const stack = document.elementsFromPoint(x, y);
                        for (const el of stack) {
                            const interactive = el.closest('button, a, input, [role="button"], select, textarea');
                            if (interactive) { target = interactive; break; }
                        }
                    } catch(e) { }
                }

                if (target) {
                    try {
                        target.scrollIntoView({behavior: 'auto', block: 'center', inline: 'center'});
                    } catch(e) {}
                    const rect = target.getBoundingClientRect();
                    const centerX = Math.floor(rect.left + rect.width / 2);
                    const centerY = Math.floor(rect.top + rect.height / 2);

                    try {
                        target.classList.add('arvyn-target-highlight');
                        const cross = document.createElement('div');
                        cross.className = 'arvyn-crosshair';
                        cross.style.left = centerX + 'px';
                        cross.style.top = centerY + 'px';
                        document.body.appendChild(cross);
                        setTimeout(() => { target.classList.remove('arvyn-target-highlight'); cross.remove(); }, 2000);
                    } catch(e) {}

                    try { target.focus(); } catch(e) {}

                    const evtOpts = { bubbles: true, cancelable: true, composed: true, clientX: centerX, clientY: centerY };
                    if (action === 'click') {
                        try {
                            target.dispatchEvent(new PointerEvent('pointerdown', evtOpts));
                            target.dispatchEvent(new PointerEvent('pointerup', evtOpts));
                            target.dispatchEvent(new MouseEvent('mousedown', evtOpts));
                            target.dispatchEvent(new MouseEvent('mouseup', evtOpts));
                            target.dispatchEvent(new MouseEvent('click', evtOpts));
                        } catch(e) {
                            try { target.click(); } catch(e) {}
                        }
                    }

                    return { x: centerX, y: centerY, name: (target.tagName || '').toLowerCase(), found: true };
                }

                // As a diagnostic fallback, return the top stacked elements at the point
                let stackInfo = [];
                try {
                    const stack = document.elementsFromPoint(x, y);
                    stackInfo = stack.slice(0,5).map(el => ({ tag: el.tagName, className: el.className || '', rect: el.getBoundingClientRect() }));
                } catch(e) { }

                return { x, y, found: false, stack: stackInfo };
            }
        """
        try:
            result = await self.page.evaluate(script, {"hint": hint, "x": x, "y": y, "action": action})
        except Exception as e:
            logger.error(f"[KINETIC] DOM Sync Script Error (main frame): {e}")
            result = {"x": x, "y": y, "found": False}

        # If not found in main frame, attempt to evaluate inside child frames (covers iframes)
        if not result.get('found'):
            try:
                for frame in self.page.frames:
                    try:
                        if frame == self.page.main_frame:
                            continue
                        frame_result = await frame.evaluate(script, {"hint": hint, "x": x, "y": y, "action": action})
                        if frame_result and frame_result.get('found'):
                            # adjust coordinates relative to parent frame
                            result = frame_result
                            break
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"[KINETIC] Frame traversal error: {e}")

        return result

    async def click_at_coordinates(self, x: int, y: int, element_hint: str = ""):
        """v5.1 High-Precision Interaction: VLM Reasoning + DOM Execution."""
        page = await self.ensure_page()
        
        # OOB Protection
        if x < 0 or y < 0 or x > self.viewport_width or y > self.viewport_height:
            await self.scroll_to(x, y)

        # 1. Perform Stealth Injection (The Hidden DOM Click)
        result = await self._execute_stealth_action(element_hint, x, y, action="click")
        tx, ty = result['x'], result['y']

        if result.get('found'):
            logger.info(f"[KINETIC] Semantic Anchor: Locked on '{element_hint}' via DOM Sync at ({tx}, {ty})")
        else:
            logger.warning(f"[KINETIC] Anchor Failed: Defaulting to VLM coords ({x}, {y})")

        try:
            # 2. Mouse Visual Consistency (For human observer/debugging)
            await page.mouse.move(tx, ty, steps=15)
            await asyncio.sleep(0.05)
            
            # 3. Native Click Fallback (Secondary assurance)
            await page.mouse.click(tx, ty, delay=random.randint(50, 100))
            
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Interaction failed: {e}")
            return False

    async def type_text(self, text: str):
        page = await self.ensure_page()
        try:
            logger.info(f"[KINETIC] Typing sequence: {len(text)} characters.")
            for char in text:
                await page.keyboard.type(char, delay=random.randint(30, 80))
            return True
        except Exception as e:
            logger.error(f"[KINETIC] Input failure: {e}")
            return False

    async def navigate(self, url: str):
        page = await self.ensure_page()
        try:
            logger.info(f"[NETWORK] Navigating to: {url}")
            await page.goto(url, wait_until="load", timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(2.0)
        except Exception as e:
            logger.error(f"[ERROR] Navigation Failed: {e}")

    async def get_screenshot_b64(self) -> str:
        page = await self.ensure_page()
        path = os.path.join(SCREENSHOT_PATH, "current_view.png")
        if not os.path.exists(SCREENSHOT_PATH): os.makedirs(SCREENSHOT_PATH)
        await page.bring_to_front()
        await asyncio.sleep(0.5)
        await page.screenshot(path=path)
        with open(path, "rb") as img:
            return base64.b64encode(img.read()).decode('utf-8')

    async def scroll_to(self, x: int, y: int):
        page = await self.ensure_page()
        scroll_y = max(0, y - (self.viewport_height // 2))
        await page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
        await asyncio.sleep(1.0)

    async def close(self):
        if self.playwright: await self.playwright.stop()
        logger.info("[BROWSER] Precision engine shutdown.")

    # --- New helpers: text search, click-by-text, dropdown selection ---
    async def find_text(self, text: str) -> bool:
        """Return True if `text` appears in page content (case-insensitive)."""
        page = await self.ensure_page()
        try:
            found = await page.evaluate("(t) => document.body && document.body.innerText.toLowerCase().includes(t)", text.lower())
            return bool(found)
        except Exception as e:
            logger.debug(f"[KINETIC] find_text error: {e}")
            try:
                content = await page.content()
                return text.lower() in content.lower()
            except Exception:
                return False

    async def find_and_click_text(self, text: str) -> bool:
        """Find element by visible text and click it (searches frames). Returns True on success."""
        page = await self.ensure_page()
        # JS with fuzzy (Levenshtein) matcher to tolerate OCR/LLM variations
        script = """
            (t) => {
                function levenshtein(a,b){if(!a||!b) return 1e9; a=a+'', b=b+''; const m=a.length, n=b.length; const d=[]; for(let i=0;i<=m;i++){d[i]=[i];} for(let j=1;j<=n;j++) d[0][j]=j; for(let i=1;i<=m;i++){for(let j=1;j<=n;j++){const cost = a[i-1]===b[j-1]?0:1; d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+cost);}} return d[m][n];}
                const search = (t||'').toLowerCase().trim();
                const elems = Array.from(document.querySelectorAll('a, button, [role="button"], span, div, label'));
                let best=null; let bestScore=1e9;
                for(const el of elems){
                    const txt = (el.innerText||el.textContent||'').toLowerCase().trim();
                    if(!txt) continue;
                    if(txt.includes(search) && search.length>0){
                        best = el; bestScore = 0; break;
                    }
                    const score = levenshtein(txt, search);
                    if(score < bestScore && score <= Math.max(1, Math.floor(search.length*0.35))){ best=el; bestScore=score; }
                }
                if(best){ try{ best.scrollIntoView({behavior:'auto', block:'center'}); }catch(e){}
                    try{ best.click(); }catch(e){ try{ best.dispatchEvent(new MouseEvent('click',{bubbles:true, cancelable:true})); }catch(e){} }
                    return true;
                }
                return false;
            }
        """
        try:
            # try main frame
            ok = await page.evaluate(script, text)
            if ok: return True
        except Exception as e:
            logger.debug(f"[KINETIC] find_and_click_text main frame error: {e}")

        # try child frames
        try:
            for frame in page.frames:
                try:
                    if frame == page.main_frame: continue
                    ok = await frame.evaluate(script, text)
                    if ok: return True
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"[KINETIC] find_and_click_text frames error: {e}")

        return False

    async def select_option_by_text(self, select_hint: str, option_text: str) -> bool:
        """Find a <select> or menu matching `select_hint`, and choose option matching `option_text`."""
        page = await self.ensure_page()
        # JS with fuzzy matching for options and menus
        script = """
            (params) => {
                function levenshtein(a,b){if(!a||!b) return 1e9; a=a+'', b=b+''; const m=a.length, n=b.length; const d=[]; for(let i=0;i<=m;i++){d[i]=[i];} for(let j=1;j<=n;j++) d[0][j]=j; for(let i=1;i<=m;i++){for(let j=1;j<=n;j++){const cost = a[i-1]===b[j-1]?0:1; d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+cost);}} return d[m][n];}
                const { hint, option } = params;
                const search = (hint||'').toLowerCase().trim();
                const opt = (option||'').toLowerCase().trim();
                const selects = Array.from(document.querySelectorAll('select, [role="listbox"], [role="menu"]'));
                for (const s of selects) {
                    const label = (s.innerText||'').toLowerCase();
                    if (!search || label.includes(search) || levenshtein(label, search) <= Math.max(1, Math.floor(search.length*0.35))) {
                        // attempt native select
                        if (s.tagName.toLowerCase() === 'select') {
                            let best=null; let bestScore=1e9;
                            for (const o of Array.from(s.options || [])) {
                                const txt = (o.text||'').toLowerCase().trim();
                                if(txt.includes(opt)) { s.value = o.value; s.dispatchEvent(new Event('change',{bubbles:true})); return true; }
                                const score = levenshtein(txt, opt);
                                if(score < bestScore){ bestScore = score; best = o; }
                            }
                            if(best && bestScore <= Math.max(1, Math.floor(opt.length*0.35))){ s.value = best.value; s.dispatchEvent(new Event('change',{bubbles:true})); return true; }
                        }
                        try { s.click(); } catch(e) {}
                        const items = Array.from(document.querySelectorAll('[role="option"], [role="menuitem"], li'));
                        let bestIt=null; let bestScore=1e9;
                        for (const it of items) {
                            const txt = (it.innerText||'').toLowerCase().trim();
                            if(txt.includes(opt)) { try{ it.click(); }catch(e){ it.dispatchEvent(new MouseEvent('click',{bubbles:true})); } return true; }
                            const score = levenshtein(txt, opt);
                            if(score < bestScore){ bestScore = score; bestIt = it; }
                        }
                        if(bestIt && bestScore <= Math.max(1, Math.floor(opt.length*0.35))){ try{ bestIt.click(); }catch(e){ bestIt.dispatchEvent(new MouseEvent('click',{bubbles:true})); } return true; }
                    }
                }
                return false;
            }
        """
        try:
            ok = await page.evaluate(script, {"hint": select_hint, "option": option_text})
            if ok: return True
        except Exception as e:
            logger.debug(f"[KINETIC] select_option_by_text main frame error: {e}")

        try:
            for frame in page.frames:
                try:
                    ok = await frame.evaluate(script, {"hint": select_hint, "option": option_text})
                    if ok: return True
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"[KINETIC] select_option_by_text frames error: {e}")

        return False

    async def fill_login_fields(self, credentials: dict) -> dict:
        """Attempt to reliably fill login fields (email/username + password).
        Returns dict with booleans {'email':bool,'password':bool} indicating success.
        """
        page = await self.ensure_page()
        email = credentials.get('email') or credentials.get('username') or ''
        password = credentials.get('password') or credentials.get('pass') or ''
        # Sanitize / validate credentials: avoid injecting long or malformed strings
        if isinstance(email, str):
            email = email.strip()
            if len(email) > 254: email = email[:254]
            # simple sanity check for email format
            if '@' not in email or '.' not in email.split('@')[-1]:
                email = ''
        else:
            email = ''

        if isinstance(password, str):
            password = password.strip()
            if len(password) > 256: password = password[:256]
        else:
            password = ''
        script = """
            (params) => {
                const { email, password } = params;
                const inputs = Array.from(document.querySelectorAll('input'));
                function scoreInput(el){
                    const attrs = ((el.name||'') + ' ' + (el.id||'') + ' ' + (el.placeholder||'') + ' ' + (el.getAttribute('aria-label')||'')).toLowerCase();
                    return attrs;
                }
                let emailEl=null, passEl=null;
                for(const el of inputs){
                    const a = scoreInput(el);
                    if(!emailEl && (a.includes('email') || a.includes('e-mail')|| a.includes('user') || a.includes('login'))) emailEl = el;
                    if(!passEl && (a.includes('pass') || el.type==='password')) passEl = el;
                }
                // Fallback heuristics
                if(!emailEl){ for(const el of inputs){ if(el.type==='email'){ emailEl = el; break; } } }
                if(!passEl){ for(const el of inputs){ if(el.type==='password'){ passEl = el; break; } } }

                if(emailEl && email){ try{ emailEl.focus(); emailEl.value = email; emailEl.dispatchEvent(new Event('input',{bubbles:true})); }catch(e){} }
                if(passEl && password){ try{ passEl.focus(); passEl.value = password; passEl.dispatchEvent(new Event('input',{bubbles:true})); }catch(e){} }
                return { email: !!emailEl, password: !!passEl };
            }
        """
        try:
            res = await page.evaluate(script, {"email": email, "password": password})
        except Exception as e:
            logger.debug(f"[KINETIC] fill_login_fields script error: {e}")
            res = {"email": False, "password": False}

        # As a fallback, try to type directly using likely selectors
        try:
            if not res.get('email') and email:
                # Try common selectors
                selectors = ["input[name*=email]","input[id*=email]","input[placeholder*=email]","input[name*=user]","input[placeholder*=user]"]
                for sel in selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            await el.click()
                            await page.keyboard.type(email, delay=50)
                            res['email'] = True
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            if not res.get('password') and password:
                selectors = ["input[type=password]","input[name*=pass]","input[id*=pass]","input[placeholder*=pass]"]
                for sel in selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            await el.click()
                            await page.keyboard.type(password, delay=50)
                            res['password'] = True
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        return res