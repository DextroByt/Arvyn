import json
import logging
import asyncio
import time
import sys
from typing import Dict, List, Any, Union, Literal, Optional
from langgraph.graph import StateGraph, END

# Use high-fidelity exports from upgraded config
from config import (
    logger, 
    QUBRID_MODEL_NAME, 
    VIEWPORT_WIDTH, 
    VIEWPORT_HEIGHT,
    DASHBOARD_SIZE
)
from core.state_schema import AgentState
from core.qwen_logic import QwenBrain
from tools.browser import ArvynBrowser
from tools.data_store import ProfileManager
from tools.voice import ArvynVoice
from core.session_manager import SessionManager

class ArvynOrchestrator:
    """
    Superior Autonomous Orchestrator for Agent Arvyn (v5.1 - Hardened Semantic Sync).
    v5.1 UPGRADE: Supports Hardened Direct-Injection Clicking to bypass UI overlays.
    FIXED: Resolves 'No Click' loops by passing precise Semantic Anchors to the Browser.
    PRESERVED: All Qubrid Vision-Reasoning, Dynamic Drift Correction, and Session Auditing.
    """

    def __init__(self, model_name: str = QUBRID_MODEL_NAME):
        self.brain = QwenBrain(model_name=model_name)
        self.browser = ArvynBrowser(headless=False)
        self.profile = ProfileManager()
        self.voice = ArvynVoice()
        self.sessions = SessionManager()
        # Increase Python recursion limit to avoid langgraph recursion errors
        try:
            sys.setrecursionlimit(10000)
        except Exception:
            pass
        self.app = None
        self.workflow = self._create_workflow()
        
        self.session_log = []
        # Track repeated element interactions to apply scaling offsets
        self.interaction_attempts = {}
        # Safety guard for ASK_USER loops
        self.consecutive_ask_count = 0
        
        logger.info(f"🚀 Arvyn Core v5.1: Autonomous Orchestrator (Hardened Sync) active.")

    async def init_app(self, checkpointer):
        """Compiles the LangGraph for Full Autonomy (Zero-Authorization)."""
        if self.app is None:
            try:
                # Increase recursion limit for complex autonomous graphs
                self.app = self.workflow.compile(
                    checkpointer=checkpointer,
                    recursion_limit=200
                )
            except TypeError:
                # Fallback if the compile signature doesn't accept recursion_limit
                self.app = self.workflow.compile(checkpointer=checkpointer)
            logger.info("✅ Arvyn Autonomous Core: Logic layers compiled for Zero-Auth flow.")

    async def cleanup(self):
        """Graceful release of browser and kinetic resources."""
        if self.browser:
            self._add_to_session_log("system", "Deactivating hardened kinetic layer...")
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"Cleanup Error: {e}")

    def _create_workflow(self) -> StateGraph:
        """Defines the interaction loop: Discovery -> Observe -> Reason -> Act."""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("intent_parser", self._node_parse_intent)
        workflow.add_node("site_discovery", self._node_site_discovery)
        workflow.add_node("autonomous_executor", self._node_autonomous_executor)
        workflow.add_node("human_interaction_node", self._node_wait_for_user)

        workflow.set_entry_point("intent_parser")
        
        workflow.add_edge("intent_parser", "site_discovery")
        workflow.add_edge("site_discovery", "autonomous_executor")
        
        workflow.add_conditional_edges(
            "autonomous_executor",
            self._decide_next_step,
            {
                "continue_loop": "autonomous_executor",
                "ask_user": "human_interaction_node",
                "finish_task": END 
            }
        )
        
        workflow.add_edge("human_interaction_node", "autonomous_executor")
        return workflow

    def _add_to_session_log(self, step: str, status: str):
        """Structured auditing for the Command Center Dashboard."""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{step.upper()}] {status}"
        self.session_log.append(entry)
        logger.info(f"📊 {entry}")

    async def _node_parse_intent(self, state: AgentState) -> Dict[str, Any]:
        self._add_to_session_log("intent_parser", "Processing natural language command...")
        last_message = state["messages"][-1]
        content = last_message.content if hasattr(last_message, 'content') else str(last_message)

        try:
            intent_obj = await self.brain.parse_intent(content)
            intent_dict = intent_obj.model_dump()
            provider = intent_dict.get('provider', 'Rio Finance Bank')
            self._add_to_session_log("intent_parser", f"Target Locked: {provider}")
            # Start a short-lived session for task tracking
            task_action = intent_dict.get('action', 'QUERY')
            sess = self.sessions.start_session(task_action, {"provider": provider})
            self._add_to_session_log('session', f"Session started: {sess.id} for {task_action}")

            return {
                "intent": intent_dict,
                "task_history": [],
                "current_step": f"Initiating workflow for {provider}...",
                "session_id": sess.id
            }
        except Exception as e:
            logger.error(f"Intent Extraction Failure: {e}")
            return {"current_step": "Clarification required.", "intent": None}

    def _resolve_target_url(self, provider_name: str) -> str:
        """Improved resolution logic to prevent unwanted redirection."""
        norm_name = provider_name.upper().replace(" ", "_")
        url = self.profile.get_verified_url(norm_name)
        if url:
            return url
        
        RIO_URL = "https://roshan-chaudhary13.github.io/rio_finance_bank/"
        rio_keywords = ["rio finance", "rio bank", "dummy bank"]
        if any(key in provider_name.lower() for key in rio_keywords):
            return RIO_URL
            
        return f"https://www.google.com/search?q={provider_name}+official+site"

    async def _node_site_discovery(self, state: AgentState) -> Dict[str, Any]:
        """Navigates and prepares for the Auto-Login Check."""
        intent = state.get("intent") or {}
        provider = intent.get("provider", "Rio Finance Bank")
        target_url = self._resolve_target_url(provider)

        try:
            page = await self.browser.ensure_page()
            if target_url not in page.url or page.url == "about:blank":
                self._add_to_session_log("discovery", f"Connecting to secure portal: {target_url}")
                await self.browser.navigate(target_url)
                await asyncio.sleep(4.0)
            
            self._add_to_session_log("security", "STATUS: Verifying Login/Session state...")
            return {"current_step": f"Connection secured. Checking login status..."}
            
        except Exception as e:
            self._add_to_session_log("error", f"Portal connection error: {str(e)}")
            return {"current_step": "Discovery retry required..."}

    async def _node_autonomous_executor(self, state: AgentState) -> Dict[str, Any]:
        """
        Main autonomous loop using Qubrid/Qwen-VL.
        ENHANCED: v5.1 Hardened Interaction utilizes direct DOM injection success signals.
        FIXED: Coordinates are 'anchored' to elements via Browser-level Semantic Sync.
        """
        self._add_to_session_log("executor", "Observing UI state...")
        
        intent = state.get("intent")
        history = state.get("task_history", [])
        
        if not intent:
            return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": "I've lost the objective."}

        # STABILIZE: Ensure page elements are static before visual reasoning
        await asyncio.sleep(1.0)
        screenshot = await self.browser.get_screenshot_b64()
        provider_name = intent.get("provider", "Rio Finance Bank")

        # Enforce section targeting for critical actions (e.g., PAY_BILL)
        target_action = intent.get('action', '').upper() if intent else ''
        # Heuristic: infer bill_type from the last user message for preference matching
        bill_type = None
        try:
            last_msg_obj = state.get('messages', [])[-1] if state.get('messages') else None
            last_msg_text = last_msg_obj.content if last_msg_obj and hasattr(last_msg_obj, 'content') else str(last_msg_obj or '')
            lm = (last_msg_text or '').lower()
            if 'electric' in lm or 'electricity' in lm:
                bill_type = 'ELECTRICITY'
            elif 'mobile' in lm or 'phone' in lm:
                bill_type = 'MOBILE'
            elif 'internet' in lm or 'broadband' in lm or 'wifi' in lm:
                bill_type = 'INTERNET'
        except Exception:
            bill_type = None

        # --- VALIDATION: Check Amount for BUY_GOLD ---
        if target_action == 'BUY_GOLD':
            amount = intent.get('amount')
            if not amount:
                # If amount missing in intent, extraction failed or wasn't provided.
                return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": "Please specify the amount for the gold purchase."}

        async def _ensure_on_bill_page(retries: int = 2) -> bool:
            """Ensure the current page is the billing/payment page; try to find and click relevant links if not."""
            bill_keywords = ['bill', 'pay bill', 'bill payment', 'electricity bill', 'pay my bill']
            # quick check
            for kw in bill_keywords:
                try:
                    if await self.browser.find_text(kw):
                        return True
                except Exception:
                    continue

            # try to find links/buttons that lead to bills
            candidates = ['pay bill', 'bill payment', 'bills', 'pay my bill', 'electricity', 'payments']
            for c in candidates:
                try:
                    clicked = await self.browser.find_and_click_text(c)
                    if clicked:
                        await asyncio.sleep(2.5)
                        # verify again
                        for kw in bill_keywords:
                            if await self.browser.find_text(kw):
                                return True
                except Exception:
                    continue

            return False
        
        goal = (
            f"GOAL: Execute {intent.get('action')} on {provider_name}. "
            f"Identify target 'element_name' (label/text) for Semantic Sync. "
            f"Use ONLY data in 'USER DATA'. DO NOT ask for permission."
        )
        
        # Inject Amount into Goal for Visual Reasoner
        if target_action == 'BUY_GOLD' and intent.get('amount'):
            goal += f" REQUIRED AMOUNT: {intent.get('amount')}."

        
        user_context = self.profile.get_provider_details(provider_name)
        user_context.update(self.profile.get_data().get("personal_info", {}))

        # --- Bill payment flow helpers (class-level orchestration) ---
        async def _ensure_on_bill_page_local(retries: int = 2) -> bool:
            bill_keywords = ['bill', 'pay bill', 'bill payment', 'electricity', 'electricity bill']
            for attempt in range(retries + 1):
                try:
                    for kw in bill_keywords:
                        if await self.browser.find_text(kw):
                            return True
                except Exception:
                    pass

                # Try clicking common navigation labels that likely lead to bills
                candidates = ['bills', 'pay bill', 'bill payment', 'payments', 'electricity']
                for c in candidates:
                    try:
                        if await self.browser.find_and_click_text(c):
                            await asyncio.sleep(2.0)
                            break
                    except Exception:
                        continue

                # If profile has a verified payment URL, navigate there
                try:
                    verified = self.profile.get_verified_url(provider_name.upper().replace(' ', '_'))
                    if verified:
                        await self.browser.navigate(verified)
                        await asyncio.sleep(2.0)
                except Exception:
                    pass

            # Final check
            try:
                for kw in bill_keywords:
                    if await self.browser.find_text(kw):
                        return True
            except Exception:
                pass
            return False

        async def _execute_bill_payment_local() -> Dict[str, Any]:
            """Sequence: ensure bill page -> find provider/bill entry -> click pay -> choose method -> confirm."""
            # 1) Ensure on bill page
            if not await _ensure_on_bill_page_local(retries=2):
                return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": "I can't reach the bill payment section."}
            # 2) Determine target bill type from user message
            # Scan last few messages for context, not just the very last one
            msgs = state.get('messages', [])
            bill_type = None
            
            # Iterate backwards through last 3 messages to find intent
            for m in reversed(msgs[-3:]):
                content = (m.content if hasattr(m, 'content') else str(m)).lower()
                if 'electric' in content or 'electricity' in content or 'power' in content:
                    bill_type = 'ELECTRICITY'
                    break
                elif 'mobile' in content or 'phone' in content or 'recharge' in content:
                    bill_type = 'MOBILE'
                    break
                elif 'internet' in content or 'broadband' in content or 'wifi' in content or 'fiber' in content:
                    bill_type = 'INTERNET'
                    break

            # fallback to automation preferences ONLY if bill_type is still None
            # And prevent defaulting to the first one if multiple are set to auto_select—this causes the "Always Electricity" bug.
            if not bill_type:
                prefs = self.profile.get_data().get('automation_preferences', {}).get('bill_payments', [])
                auto_candidates = [p for p in prefs if p.get('auto_select')]
                
                if len(auto_candidates) == 1:
                    # Only one preferred bill type? Safe to auto-select.
                    bill_type = auto_candidates[0].get('category')
                elif len(auto_candidates) > 1:
                    # Ambiguous! Multiple bills marked for auto-pay. Don't guess 'Electricity'.
                    # We will likely find "Electricity", "Mobile", etc. on screen and click one, or ask user.
                    pass 

            # 2.1) CLICK CATEGORY (e.g. "Electricity", "Mobile")
            if bill_type:
                category_variants = []
                if bill_type == 'ELECTRICITY':
                    category_variants = ['Electricity', 'Electricity Bill', 'Power', 'Light Bill']
                elif bill_type == 'MOBILE':
                    category_variants = ['Mobile', 'Prepaid', 'Postpaid', 'Recharge', 'Mobile Recharge']
                elif bill_type == 'INTERNET':
                    category_variants = ['Broadband', 'Internet', 'Fiber', 'Landline']

                cat_clicked = False
                for cv in category_variants:
                    try:
                        # Use exact match preference to avoid 'Mobile' matching 'Automobile' etc.
                        if await self.browser.find_and_click_text(cv, exact=True):
                            self._add_to_session_log('executor', f"Selected Category: {cv}")
                            cat_clicked = True
                            await asyncio.sleep(2.0)
                            break
                    except Exception:
                        continue
                
                if not cat_clicked:
                     self._add_to_session_log('executor', f"Could not explicitly click category for {bill_type}, proceeding to provider search...")

            # 2.2) SELECT PROVIDER
            target_provider_name = provider_name
            consumer_number = None

            prefs = self.profile.get_data().get('automation_preferences', {}).get('bill_payments', [])
            matched_pref = None
            
            # Logic: Match provider name explicitly OR match by bill_type
            if prefs:
                for p in prefs:
                    pname = p.get('provider_name', '')
                    # 1. Match by specific provider name if known
                    if pname and provider_name and pname.lower() in provider_name.lower():
                        matched_pref = p
                        break
                    # 2. Match by Category (if we have a focused bill_type)
                    if bill_type and p.get('category') == bill_type and p.get('auto_select'):
                        matched_pref = p
                        break # Found the preference for this category
            
            if matched_pref:
                target_provider_name = matched_pref.get('provider_name')
                consumer_number = matched_pref.get('consumer_number') or matched_pref.get('mobile_number')
            
            if target_provider_name and target_provider_name.lower() != 'rio finance bank':
                 self._add_to_session_log('executor', f"Selecting Provider: {target_provider_name}")
                 try:
                     if not await self.browser.find_and_click_text(target_provider_name, exact=True):
                         pass
                     await asyncio.sleep(2.0) 
                 except Exception:
                     pass

            # 2.3) FILL CONSUMER NUMBER
            if consumer_number:
                self._add_to_session_log('executor', f"Injecting Consumer ID: {consumer_number}")
                cnum_script = """
                (val) => {
                    const inputs = Array.from(document.querySelectorAll('input'));
                    let best = null;
                    for(const el of inputs){
                        const txt = ((el.placeholder||'') + ' ' + (el.name||'') + ' ' + (el.id||'') + ' ' + (el.getAttribute('aria-label')||'')).toLowerCase();
                        if(txt.includes('consumer') || txt.includes('customer') || txt.includes('number') || txt.includes('mobile') || txt.includes('id')){
                             if(!txt.includes('email') && !txt.includes('user')){ best = el; break; }
                        }
                    }
                    if(best){ best.focus(); best.value = val; best.dispatchEvent(new Event('input', { bubbles: true })); best.dispatchEvent(new Event('change', { bubbles: true })); return true; }
                    return false;
                }
                """
                try:
                    await self.browser.page.evaluate(cnum_script, str(consumer_number))
                    await self.browser.type_text(str(consumer_number))
                    await asyncio.sleep(1.0)
                except Exception:
                    pass

            # 2.4) FETCH BILL / PROCEED
            fetch_labels = ['Fetch Bill', 'Get Bill', 'View Bill', 'Proceed', 'Next', 'Continue']
            for fl in fetch_labels:
                try:
                    if await self.browser.find_and_click_text(fl):
                        await asyncio.sleep(3.0)
                        break
                except Exception:
                    continue
            
            # NOW try to find the "Pay" button
            pay_entry_labels = ['Pay', 'Pay Now', 'Pay Bill', 'Make Payment']
            found_entry = False
            for pl in pay_entry_labels:
                 try:
                     if await self.browser.find_and_click_text(pl):
                         found_entry = True
                         await asyncio.sleep(2.0)
                         break
                 except Exception:
                     continue

            if not found_entry and not await self.browser.find_text('UPI'):
                  return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": "I selected the details but couldn't find the 'Pay' button. Shall I try manual steps?"}

            # 3) On the payment page, select a payment method
            settings = self.profile.get_data().get('settings', {})
            personal_info = self.profile.get_data().get('personal_info', {})
            preferred = settings.get('default_payment_method') or 'UPI'
            selected_method = None
            
            self._add_to_session_log('executor', f"Selecting payment method: {preferred}")
            
            # Refined keywords to prevent 'Select All' behavior
            method_keywords = {
                'UPI': ['UPI', 'Unified Payment Interface', 'VPA', 'GooglePay', 'PhonePe', 'Paytm'],
                'CREDIT_CARD': ['Credit Card', 'Debit Card'], # Removed generic 'Card' to avoid ambiguity
                'NET_BANKING': ['Net Banking', 'Internet Banking']
            }
            
            target_keywords = method_keywords.get(preferred, [preferred])
            if preferred == 'UPI': 
                 # Prioritize explicit UPI text
                 if 'UPI' not in target_keywords: target_keywords.insert(0, 'UPI')

            method_clicked = False
            for kw in target_keywords:
                try:
                    # Attempt click. loop breaks immediately on success.
                    if await self.browser.find_and_click_text(kw, exact=True):
                        selected_method = preferred
                        method_clicked = True
                        await asyncio.sleep(1.5)
                        break
                except Exception: continue
            
            if not method_clicked:
                 self._add_to_session_log('executor', f"Could not explicitly select {preferred}, checking if already visible...")

            # If UPI is selected or default, inject details
            if selected_method == 'UPI' or (not selected_method and preferred == 'UPI'):
                # Check for UPI fields and inject
                upi_id = personal_info.get('upi id') or personal_info.get('upi_id')
                upi_pin = personal_info.get('upi_pin') or personal_info.get('pin')
                
                if upi_id:
                    self._add_to_session_log('kinetic', f"Injecting UPI ID for {upi_id}...")
                    await self.browser.fill_upi_details(upi_id, upi_pin if upi_pin else "")
                else:
                     self._add_to_session_log('kinetic', "No UPI ID found in profile. Skipping injection.")

            # 4) Attempt to click confirm/pay buttons
            confirm_labels = ['Pay Now', 'Pay', 'Proceed to Pay', 'Make Payment', 'Confirm']
            paid = False
            for lab in confirm_labels:
                try:
                    if await self.browser.find_and_click_text(lab):
                        paid = True
                        await asyncio.sleep(2.5)
                        break
                except Exception:
                    continue

            if not paid:
                return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": "Reached payment step but couldn't finish payment automatically. Provide payment confirmation?"}
            # 5) Success: navigate back to dashboard/safe page and clear task
            try:
                await self.browser.navigate('about:blank')
            except Exception:
                pass
            try:
                self.profile.clear_task()
            except Exception:
                pass

            self._add_to_session_log('executor', 'Returning to dashboard and stopping current task.')
            return {"browser_context": {"action_type": "FINISHED"}, "current_step": "Bill Task Completed. Payment processed via UPI."}


        self._add_to_session_log("brain", f"Qubrid Engine: Analyzing page for {intent.get('action')}...")
        analysis = await self.brain.analyze_page_for_action(screenshot, goal, history, user_context)

        if not isinstance(analysis, dict):
            analysis = {"action_type": "ASK_USER", "thought": "Invalid analysis format."}

        action_type = str(analysis.get("action_type", "ASK_USER"))
        current_history = history.copy()
        element_name = str(analysis.get("element_name", ""))
        input_text = str(analysis.get("input_text", ""))

        # Enforce target section when user intent is to pay a bill
        if target_action == 'PAY_BILL':
            # Track active goal in profile for stateful behavior
            try:
                self.profile.track_task(f"PAY_BILL::{provider_name}")
            except Exception:
                pass

            on_bill = await _ensure_on_bill_page()
            if not on_bill:
                self._add_to_session_log('navigation', 'Could not find billing page; attempting recovery...')
                # If failed to reach bill page after recovery attempts, ask user
                if not await _ensure_on_bill_page(retries=1):
                    return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": "I couldn't reach the bill payment page. Do you want me to keep trying?"}

            # If we are on the bill page, run the strict bill payment flow
            exec_result = await _execute_bill_payment_local()
            # If the flow finished or requested user input, return early
            if exec_result.get('browser_context', {}).get('action_type') in ('FINISHED', 'ASK_USER'):
                if exec_result.get('browser_context', {}).get('action_type') == 'FINISHED':
                    self._add_to_session_log('executor', '✅ Automated bill payment completed.')
                    try:
                        self.profile.clear_task()
                    except Exception:
                        pass
                return exec_result

        if action_type in ["CLICK", "TYPE"]:
            self.consecutive_ask_count = 0
            coords = analysis.get("coordinates")
            if coords and len(coords) == 4:
                # 0-1000 Normalized Coordinate Translation
                ymin, xmin, ymax, xmax = coords
                cx = round(((xmin + xmax) / 2) * (VIEWPORT_WIDTH / 1000))
                cy = round(((ymin + ymax) / 2) * (VIEWPORT_HEIGHT / 1000))
                
                interaction_key = f"{action_type}_{element_name.lower()}"
                count = self.interaction_attempts.get(interaction_key, 0)
                MAX_INTERACTION_ATTEMPTS = 6
                if count >= MAX_INTERACTION_ATTEMPTS:
                    self._add_to_session_log("safety", f"Max attempts reached for '{element_name}'. Asking user.")
                    # Mark this interaction as disabled to avoid repeated ASK_USER loops
                    try:
                        self.interaction_attempts[interaction_key] = MAX_INTERACTION_ATTEMPTS + 100
                    except Exception:
                        pass
                    # Mark session awaiting user intervention with a cooldown
                    try:
                        sess = self.sessions.get_session()
                        if sess:
                            self.sessions.update_session(awaiting_user=True, awaiting_user_until=time.time() + 300)
                    except Exception:
                        pass
                    return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": f"I've tried interacting with '{element_name}' several times without effect. Shall I keep trying?"}
                
                # Dynamic Drift Correction (Maintained as secondary safety layer)
                if count > 0:
                    offset_x = (count * 10) if count % 2 == 0 else -(count * 10)
                    offset_y = (count * 20) if count % 3 == 0 else 0 
                    cx += offset_x
                    cy += offset_y
                    self._add_to_session_log("kinetic", f"Applying drift offset {count} to improve visual search...")
                
                self.interaction_attempts[interaction_key] = count + 1
                self._add_to_session_log("kinetic", f"Executing Hardened Interaction on '{element_name}'...")
                
                # v5.1 HARDENED CALL: Browser performs direct interaction if possible
                # Special-case: if element looks like login/email/password field, attempt robust autofill first
                filled = {}
                # If user asked to PAY_BILL and we have an automation preference, try clicking that provider first
                tried_pref_click = False
                if target_action == 'PAY_BILL':
                    try:
                        prefs = self.profile.get_data().get('automation_preferences', {}).get('bill_payments', [])
                        if prefs:
                            # prefer matching category first
                            pref_name = None
                            if bill_type:
                                for p in prefs:
                                    if p.get('category') == bill_type and p.get('auto_select'):
                                        pref_name = p.get('provider_name')
                                        break
                            # fallback: if intent provider matches a preference entry, use that
                            if not pref_name:
                                for p in prefs:
                                    pname = p.get('provider_name')
                                    if pname and provider_name and pname.lower() in provider_name.lower() and p.get('auto_select'):
                                        pref_name = pname
                                        break

                            if pref_name:
                                self._add_to_session_log('kinetic', f"Attempting preferred provider click: {pref_name}")
                                clicked_pref = await self.browser.find_and_click_text(pref_name)
                                tried_pref_click = True
                                if clicked_pref:
                                    self._add_to_session_log('kinetic', f"Preferred provider '{pref_name}' clicked — bypassing VLM coords.")
                                    success = True
                                else:
                                    # continue to coordinate-based attempt below
                                    success = False
                    except Exception:
                        tried_pref_click = False
                if any(k in element_name.lower() for k in ['email', 'user', 'password', 'pass']):
                    creds = self.profile.get_provider_credentials(provider_name)
                    if creds:
                        filled = await self.browser.fill_login_fields(creds)
                        # If autofill succeeded for either, mark success
                        if filled.get('email') or filled.get('password'):
                            self._add_to_session_log('kinetic', 'Autofilled credentials from profile.')
                            success = True
                        else:
                            success = await self.browser.click_at_coordinates(cx, cy, element_hint=element_name)
                    else:
                        success = await self.browser.click_at_coordinates(cx, cy, element_hint=element_name)
                else:
                    success = await self.browser.click_at_coordinates(cx, cy, element_hint=element_name)
                if success:
                    # If autofill handled the input, skip further typing to prevent duplication/errors
                    is_autofilled = filled.get('email') or filled.get('password')
                    
                    if action_type == "TYPE" and not is_autofilled:
                        self._add_to_session_log("kinetic", "Inputting secured sequence...")
                        # Prefer profile credentials for login-related fields to avoid LLM hallucinated values
                        ename = element_name.lower()
                        creds = self.profile.get_provider_credentials(provider_name)
                        # consumer number autofill: check automation_preferences for matching provider/category
                        consumer_number = None
                        try:
                            prefs = self.profile.get_data().get('automation_preferences', {}).get('bill_payments', [])
                            if prefs:
                                # If provider explicitly listed, prefer that consumer number
                                for p in prefs:
                                    pname = p.get('provider_name','').lower() if p.get('provider_name') else ''
                                    if pname and pname in provider_name.lower():
                                        consumer_number = p.get('consumer_number') or p.get('mobile_number')
                                        break
                                # Otherwise prefer entry by category
                                if not consumer_number and bill_type:
                                    for p in prefs:
                                        if p.get('category') == bill_type:
                                            consumer_number = p.get('consumer_number') or p.get('mobile_number')
                                            break
                        except Exception:
                            consumer_number = None
                        # sanitize analysis input_text
                        if isinstance(input_text, str) and len(input_text) > 256:
                            input_text = input_text[:256]

                        if any(k in ename for k in ("email", "e-mail", "user", "username", "login")):
                            preferred = creds.get('email') or creds.get('username') or self.profile.get_data().get('personal_info', {}).get('email')
                            if preferred:
                                await self.browser.type_text(preferred)
                            else:
                                await self.browser.type_text(input_text)
                        elif any(k in ename for k in ("pass", "password", "pwd")):
                            # specialized check for transaction password
                            if 'trans' in ename or 'pin' in ename:
                                sec = self.profile.get_data().get('security_details', {})
                                t_pass = sec.get('transaction_password') or sec.get('card_pin') or sec.get('upi_pin')
                                if t_pass:
                                    await self.browser.type_text(t_pass)
                                else:
                                    # Fallback to login password if no specific transaction pin/pass found (though usually risky)
                                    preferred = creds.get('password')
                                    if preferred:
                                        await self.browser.type_text(preferred)
                                    else:
                                        await self.browser.type_text(input_text)
                            else:
                                preferred = creds.get('password')
                                if preferred:
                                    await self.browser.type_text(preferred)
                                else:
                                    await self.browser.type_text(input_text)
                        elif any(k in ename for k in ("consumer", "consumer no", "consumer number", "mobile no", "mobile")):
                            # Use automation preference consumer_number when available
                            if consumer_number:
                                await self.browser.type_text(str(consumer_number))
                            else:
                                await self.browser.type_text(input_text)
                        elif any(k in ename for k in ("amount", "worth", "value", "rupee", "inr")):
                             # Explicitly handle Amount fields for BUY_GOLD
                             if target_action == 'BUY_GOLD' and intent.get('amount'):
                                 await self.browser.type_text(str(intent.get('amount')))
                             else:
                                 await self.browser.type_text(input_text)
                        else:
                            await self.browser.type_text(input_text)

                    # If this looks like a dropdown/select interaction, attempt to set the option by visible text
                    try:
                        if element_name and input_text:
                            selected = await self.browser.select_option_by_text(element_name, input_text)
                            if selected:
                                self._add_to_session_log('kinetic', f"Selected dropdown option '{input_text}' on '{element_name}'.")
                    except Exception:
                        pass
                    
                    # POST-ACTION DELAY: Allow DOM to update
                    await asyncio.sleep(2.5)
                    current_history.append({
                        "action": action_type, 
                        "element": element_name,
                        "thought": analysis.get("thought")
                    })
                    
                    # Interaction successful; reset attempts for this specific chain
                    if len(history) > 0 and history[-1].get("element") != element_name:
                        self.interaction_attempts = {interaction_key: 1}
                else:
                    self._add_to_session_log("kinetic", "ERROR: Kinetic registration failed. Recalibrating logic...")

                # Post-click navigation enforcement: if intent was PAY_BILL but page contains 'gold', recover
                try:
                    if target_action == 'PAY_BILL' and await self.browser.find_text('gold'):
                        self._add_to_session_log('navigation', 'Detected wrong section (gold). Redirecting to bills...')
                        await _ensure_on_bill_page()
                except Exception:
                    pass

        elif action_type == "FINISHED":
            self.consecutive_ask_count = 0
            self._add_to_session_log("executor", "✅ Task completed successfully.")
        
        elif action_type == "ASK_USER":
            self.consecutive_ask_count += 1

        return {
            "screenshot": await self.browser.get_screenshot_b64(),
            "task_history": current_history,
            "browser_context": analysis,
            "current_step": str(analysis.get("thought", "Advancing autonomous workflow...")),
            "pending_question": analysis.get("voice_prompt") if action_type == "ASK_USER" else None,
            "human_approval": "approved"
        }

    async def _node_wait_for_user(self, state: AgentState) -> Dict[str, Any]:
        """Breakpoint node for manual intervention."""
        return {"current_step": "Resuming autonomous execution...", "human_approval": "approved"}

    def _decide_next_step(self, state: AgentState) -> Literal["continue_loop", "ask_user", "finish_task"]:
        analysis = state.get("browser_context", {})
        action_type = analysis.get("action_type")
        
        if action_type == "FINISHED": return "finish_task"
        
        if action_type == "ASK_USER":
            if self.consecutive_ask_count > 5:
                self._add_to_session_log("safety", "Stuck detected. Session terminated to prevent resource drain.")
                return "finish_task"
            return "ask_user"
        
        if len(state.get("task_history", [])) > 60:
            self._add_to_session_log("safety", "Maximum task depth reached.")
            return "finish_task"
            
        return "continue_loop"