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
        self.consecutive_ask_count = 0
        self.security_locked = False 
        
        logger.info(f"🚀 Arvyn Core v5.1: Autonomous Orchestrator (Hardened Sync) active.")

    async def init_app(self, checkpointer):
        """Compiles the LangGraph for Full Autonomy (Zero-Authorization)."""
        if self.app is None:
            try:
                # Increase recursion limit for complex autonomous graphs
                self.app = self.workflow.compile(
                    checkpointer=checkpointer,
                    recursion_limit=200,
                    interrupt_before=["human_interaction_node"]
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
            
            # RULE-BASED OVERRIDE: Ensure specific keywords map to PAY_BILL
            # This fixes the issue where "pay my mobile" is misclassified as NAVIGATE
            text_norm = content.lower()
            if 'pay' in text_norm and any(k in text_norm for k in ['bill', 'mobile', 'internet', 'recharge', 'electricity']):
                if intent_dict.get('action') != 'PAY_BILL':
                    self._add_to_session_log("intent_parser", "Rule-based override: Forcing action to PAY_BILL")
                    intent_dict['action'] = 'PAY_BILL'
                    intent_dict['target'] = 'UTILITY'
            
            # PROFILE UPDATE OVERRIDE
            if any(k in text_norm for k in ['profile', 'name', 'phone', 'number', 'email']) and 'update' in text_norm:
                if intent_dict.get('action') != 'UPDATE_PROFILE':
                    self._add_to_session_log("intent_parser", "Rule-based override: Forcing action to UPDATE_PROFILE")
                    intent_dict['action'] = 'UPDATE_PROFILE'

            if intent_dict.get('action') == 'CLARIFY':
                self._add_to_session_log("intent_parser", "Input ambiguous or meaningless. Requesting clarification.")
                return {"current_step": "Clarification required.", "intent": None}

            if intent_dict.get('action') == 'UPDATE_PROFILE':
                self._add_to_session_log("intent_parser", "Profile Update detected. Creating temporary memory...")
                
                # Rule-based field extraction fallback if LLM missed it
                fields = intent_dict.get('fields_to_update', {}) or {}
                if not fields:
                    import re
                    # Simple regex for "name to X"
                    name_match = re.search(r'(?:name|full name)\s+(?:to|is)\s+([^,.\n]+)', content, re.I)
                    if name_match: 
                        fields['full_name'] = name_match.group(1).strip()
                    # Simple regex for "phone to X" or "number to X"
                    phone_match = re.search(r'(?:phone|number)\s+(?:to|is)\s+(\d+)', content, re.I)
                    if phone_match:
                        fields['phone'] = phone_match.group(1).strip()
                
                # Create Temporary Memory File in user_profile format
                temp_mem_structure = {
                    "personal_info": fields
                }
                
                try:
                    with open('profile_update_memory.json', 'w') as f:
                        json.dump(temp_mem_structure, f, indent=4)
                    self._add_to_session_log("intent_parser", f"Temporary Profile Memory synced with mentioned fields: {list(fields.keys())}")
                except Exception as e:
                    logger.error(f"Failed to create temporary memory file: {e}")

                # Sync back to the intent dictionary to ensure consistent tracking
                intent_dict['fields_to_update'] = fields

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
            # Fallback intent to prevent None and subsequent tight loop
            return {
                "intent": {"action": "NAVIGATE", "target": "GENERAL", "provider": "Search"},
                "current_step": "System error occurred. Navigating to safety.",
                "task_history": []
            }

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
        """Node for Deciding and Executing Actions (Zero-Auth mode optimized)."""
        current_approval = state.get("human_approval")
        
        # --- CONCISE PAUSE: Rejection Guard ---
        if current_approval == "rejected":
            self._add_to_session_log("security", "🚫 Task rejection received. Terminating kinetic sequence.")
            self.security_locked = False
            return {
                "current_step": "TASK ABORTED",
                "browser_context": {"action_type": "FINISHED"},
                "human_approval": "rejected",
                "is_security_pause": False
            }

        # --- CONCISE PAUSE: Top-Level Security Lock Guard ---
        if self.security_locked and current_approval != "approved":
            return {
                "screenshot": await self.browser.get_screenshot_b64() if self.browser.page else None,
                "task_history": state.get("task_history", []),
                "browser_context": {"action_type": "ASK_USER", "thought": "Security Lock active. Standing by for user authorization."},
                "current_step": "AWAITING PAYMENT APPROVAL",
                "pending_question": state.get("pending_question"),
                "human_approval": None,
                "is_security_pause": True 
            }

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

        goal = (
            f"GOAL: Execute {target_action} on {provider_name}. "
            f"Target Amount: {intent.get('amount', 'Not Specified')}. "
            f"Identify target 'element_name' (label/text) for Semantic Sync. "
            f"Use ONLY data in 'USER DATA'. DO NOT ask for permission."
        )

        if target_action == 'UPDATE_PROFILE':
            fields = intent.get('fields_to_update', {}) or {}
            fields_desc = ", ".join([f"'{k}' to '{v}'" for k, v in fields.items()])
            goal = (
                f"GOAL: Update User Profile on {provider_name}. "
                f"SPECIFIC CHANGES: Update {fields_desc}. "
                f"STEPS: "
                f"1. Navigate to Profile/Account Settings page. "
                f"2. Locate the input fields for {', '.join(fields.keys())}. "
                f"3. Type the NEW values into each field. The system will automatically clear the old name before typing. "
                f"4. Click 'Save' or 'Update' once all fields are filled. "
                f"ONLY update the mentioned fields. DO NOT touch other fields. "
                f"Execute all steps autonomously without asking for confirmation."
            )
        
        if target_action == 'UPDATE_PROFILE':
            # RESTRICTIVE CONTEXT: Only use the temporary memory for profile updates
            try:
                if os.path.exists('profile_update_memory.json'):
                    with open('profile_update_memory.json', 'r') as f:
                        user_context = json.load(f)
                else:
                    user_context = intent.get('fields_to_update', {}) or {}
            except Exception:
                user_context = intent.get('fields_to_update', {}) or {}
            
            self._add_to_session_log('executor', f"Profile Update: Using restricted temporary memory context.")
        else:
            user_context = self.profile.get_data().get("personal_info", {})
            user_context.update(self.profile.get_provider_details(provider_name))

        if target_action == 'PAY_BILL':
            # Track active goal in profile for stateful behavior
            try:
                self.profile.track_task(f"PAY_BILL::{provider_name}")
            except Exception:
                pass
            
            # --- PURE AUTONOMY REFACTOR ---
            # 1. State Check: Login
            login_indicators = ['Sign In', 'Log In', 'Login', 'Sign in to Rio Finance']
            is_login_page = False
            for li in login_indicators:
                try:
                    if await self.browser.find_text(li):
                        is_login_page = True
                        break
                except Exception:
                    pass
            
            if is_login_page:
                 self._add_to_session_log('security', 'Login Required. Injecting credentials once...')
                 creds = self.profile.get_provider_credentials(provider_name)
                 if creds:
                     await self.browser.fill_login_fields(creds)
            
            if bill_type:
                goal += f" FOCUS: The user wants to pay for {bill_type}. IGNORE irrelevant options like Electricity (unless that is the target). Look for '{bill_type}' or related keywords."
            
        elif target_action == 'UPDATE_PROFILE':
            # Check for Profile link if not on profile page
            current_url = self.browser.page.url
            if 'profile' not in current_url.lower():
                self._add_to_session_log('executor', 'User is likely not on profile page. Scanning for Profile/Account links...')
                goal += " Current page is likely NOT the profile page. Look for 'Profile', 'Account', or 'User Settings' links first."

        self._add_to_session_log("brain", f"Qubrid Engine: Analyzing page for {target_action}...")
        analysis = await self.brain.analyze_page_for_action(screenshot, goal, history, user_context)

        if not isinstance(analysis, dict):
            analysis = {"action_type": "ASK_USER", "thought": "Invalid analysis format."}

        action_type = str(analysis.get("action_type", "ASK_USER"))
        current_history = history.copy()
        element_name = str(analysis.get("element_name", ""))
        input_text = str(analysis.get("input_text", ""))

        # --- CONCISE PAUSE FEATURE: Security Field Detection ---
        # Triggered for Payment Pins, Transaction Pins, UPI Pins, CVV, etc.
        # Triggered for Payment Pins, Transaction Pins, UPI Pins, CVV, etc.
        security_keywords = [
            'pin', 'transaction pin', 'upi pin', 'payment pin', 
            'cvv', 'card pin', 'security code', 'transaction password',
            'password', 'pass' # Expanded to catch all potentially sensitive auth fields
        ]
        ename_low = element_name.lower()
        is_security_field = any(k in ename_low for k in security_keywords)
        # Refined check: If it's just 'password' (login), we might skip pause if we want full autonomy for login?
        # User request was specifically about "transaction pin". 
        # But to be safe per user instructions "agent should not perform any task as long as there is no user response to the button" 
        # implies ANY sensitive triggering should probably wait if it's ambiguous.
        # However, for regular login, pausing might be annoying.
        # Let's target the "transaction pin" specifically requested by user but keep it broad enough.
        
        # If the element matches "pin" or "transaction", strictly enforce pause.
        if 'pin' in ename_low or 'transaction' in ename_low or 'cvv' in ename_low:
             is_security_field = True
        elif 'password' in ename_low and 'login' not in ename_low and 'sign' not in ename_low:
             # Assume non-login passwords might be transaction passwords
             is_security_field = True
        
        # --- REPEATED ACTION GUARD: Prevent Infinite Security Loops ---
        # If we successfully injected a PIN in the last step, but the VLM sees it again, 
        # it forces a loop. We must override this and look for a submit/continue button.
        if is_security_field and history and history[-1].get('action') == 'TYPE':
            last_el = history[-1].get('element', '').lower()
            # Fuzzy match: "Transaction PIN" vs "Enter PIN" etc.
            if element_name.lower() in last_el or last_el in element_name.lower() or 'pin' in last_el:
                 self._add_to_session_log("brain", "⚠️ RECURSION GUARD: Security Field already filled. Forcing 'Submit'.")
                 # Override VLM decision
                 action_type = "CLICK"
                 # HEURISTIC: Guess common submit names
                 element_name = "Submit" 
                 # We can try to be smarter or just rely on text fallback ("Pay", "Continue", etc)
                 # Ideally we should ask the browser to find "Pay" or "Submit" but we can just set the intent
                 # and let the existing text-finding logic handle "Submit" if coordinates fail?
                 # Actually, let's keep it simple: "Submit" often works on these forms.
                 # Or "Pay Now".
                 is_security_field = False # Bypass security lock for this corrective action

        # If it's a security field and not yet approved, we force an ASK_USER state
        if is_security_field and current_approval != "approved":
            # If already rejected earlier in the node, we shouldn't be here, but just in case:
            if current_approval == "rejected":
                 return {"browser_context": {"action_type": "FINISHED"}, "human_approval": "rejected"}
            
            self.security_locked = True
            self._add_to_session_log("security", f"🛡️ CONCISE PAUSE: '{element_name}' detected. Awaiting User Approval...")
            return {
                "browser_context": {"action_type": "ASK_USER", "thought": f"Security-sensitive field detected: {element_name}."},
                "current_step": "AWAITING PAYMENT APPROVAL",
                "pending_question": f"Please Approve or Reject the use of your {element_name}.",
                "human_approval": None,
                "is_security_pause": True 
            }


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
                if count >= 3:
                    self._add_to_session_log("kinetic", f"Standard clicks failing for '{element_name}'. Engaging FORCE CLICK (JS/Text).")
                    
                    # FORCE CLICK STRATEGY: 
                    # 1. Try Text Match Click
                    # 2. Try JS Click on focused element? No, JS click by text.
                    force_success = False
                    try:
                        if await self.browser.find_and_click_text(element_name):
                             force_success = True
                             self._add_to_session_log("kinetic", "FORCE CLICK: Text-based click successful.")
                    except Exception:
                        pass
                    
                    if not force_success:
                        # Escalation: JS Force Click on any element matching text
                        js_code = f"""
                        (text) => {{
                            const els = Array.from(document.querySelectorAll('*'));
                            const target = els.find(e => e.innerText && e.innerText.trim().toLowerCase() === text.toLowerCase() && e.offsetParent !== null);
                            if (target) {{ target.click(); return true; }}
                            return false;
                        }}
                        """
                        try:
                            if await self.browser.page.evaluate(js_code, element_name):
                                force_success = True
                                self._add_to_session_log("kinetic", "FORCE CLICK: JS injection successful.")
                        except Exception:
                             pass

                    if force_success:
                        # Reset attempts if force click worked
                        try:
                           self.interaction_attempts[interaction_key] = 1
                        except Exception: pass
                        await asyncio.sleep(4.0) # Extra stabilization after force click
                        return {
                            "screenshot": await self.browser.get_screenshot_b64(),
                            "task_history": current_history + [{"action": action_type, "element": element_name, "thought": "Force Click Executed."}],
                            "browser_context": analysis,
                            "current_step": f"Force-clicked '{element_name}'. Verifying effect...",
                            "pending_question": None,
                            "human_approval": "approved"
                        }

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
                            
                            # v5.1 FIX: Immediately attempt to click Sign In to prevent looping on input fields
                            await asyncio.sleep(1.0)
                            login_buttons = ['Sign In', 'Log In', 'Login', 'Submit', 'Continue']
                            for btn_text in login_buttons:
                                try:
                                    if await self.browser.find_and_click_text(btn_text):
                                        self._add_to_session_log('kinetic', f"Auto-clicked '{btn_text}' after autofill.")
                                        await asyncio.sleep(3.0) # Wait for navigation
                                        break
                                except Exception:
                                    continue
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

                        # Check if this is a targeted field for profile update
                        is_profile_update_field = False
                        if target_action == 'UPDATE_PROFILE':
                            def normalize(s: str) -> str:
                                return s.lower().replace("_", "").replace(" ", "")
                            
                            target_fields = intent.get('fields_to_update', {}) or {}
                            norm_ename = normalize(element_name)
                            for field_name in target_fields:
                                if normalize(field_name) in norm_ename or norm_ename in normalize(field_name):
                                    is_profile_update_field = True
                                    # Override with value from restrictive context to ensure precision
                                    ctx_val = user_context.get("personal_info", {}).get(field_name)
                                    if ctx_val:
                                        input_text = str(ctx_val)
                                    break

                        if is_profile_update_field:
                            # Trust VLM for the target, but use curated value for the text
                            self._add_to_session_log('executor', f"Updating mentioned field '{element_name}' with value from temporary memory.")
                            await self.browser.type_text(input_text)
                        elif target_action == 'UPDATE_PROFILE':
                            # DO NOT AUTO-FILL fields that were not mentioned by the user
                            self._add_to_session_log('executor', f"Skipping auto-fill for '{element_name}' (Not in update command).")
                        elif any(k in ename for k in ("email", "e-mail", "user", "username", "login")):
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
                            val_to_type = str(consumer_number) if consumer_number else str(input_text)
                            
                            # ANTI-HALLUCINATION: If the value looks like an address or contains letters where digits are expected
                            is_address = "," in val_to_type or len(val_to_type.split()) > 3
                            # Strict numeric check for specific fields
                            is_not_numeric = any(c.isalpha() for c in val_to_type.replace("+", "").replace("-", "").replace(" ", "").replace(".", "")) 
                            
                            if is_address or is_not_numeric:
                                self._add_to_session_log("brain", f"⚠️ HALLUCINATION GUARD: Value '{val_to_type}' (derived from '{input_text}') is invalid for '{element_name}'. Resetting field focus.")
                                # Reset attempt count so it doesn't get stuck in ASK_USER loop immediately
                                self.interaction_attempts[interaction_key] = 0
                                success = False 
                            else:
                                await self.browser.type_text(val_to_type)
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
                    
                    if success:
                        # POST-ACTION DELAY: Allow DOM to update
                        await asyncio.sleep(2.5)
                        self._add_to_session_log("kinetic", f"Action successful: {action_type} on {element_name}")
                        # Interaction successful; reset lock and attempts
                        self.security_locked = False # RELEASE THE LOCK
                        if len(history) > 0 and history[-1].get("element") != element_name:
                            self.interaction_attempts = {}

                        # --- SUCCESS GUARD: Check if we are done ---
                        # After an action, check if the page now says "Success" or we are back on "Dashboard"
                        # to prevent looping back to start.
                        try:
                            # Quick text check of the new state
                            page_text = await self.browser.get_page_text()
                            page_text_lower = page_text.lower()
                            success_indicators = [
                                "payment successful", "transaction successful", "order placed successfully", 
                                "congratulations", "success", "confirmed", "receipt"
                            ]
                            is_success = any(ind in page_text_lower for ind in success_indicators)
                            
                            # Also check if we returned to dashboard after some progress
                            is_dashboard = "dashboard" in page_text_lower and "balance" in page_text_lower
                            
                            if (is_success or is_dashboard) and len(current_history) > 2:
                                self._add_to_session_log("brain", "✅ SUCCESS CONFIRMED: Completing task sequence.")
                                return {
                                    "screenshot": await self.browser.get_screenshot_b64(),
                                    "task_history": current_history,
                                    "browser_context": {"action_type": "FINISHED"}, # Force Finish
                                    "current_step": "Task Completed Successfully.",
                                    "pending_question": None,
                                    "human_approval": None,
                                    "is_security_pause": False
                                }
                        except Exception:
                            pass
                        
                        # Return state with updated history and reset approval
                        return {
                            "screenshot": await self.browser.get_screenshot_b64(),
                            "task_history": current_history + [{
                                "action": action_type, 
                                "element": element_name, 
                                "thought": analysis.get("thought")
                            }],
                            "browser_context": analysis,
                            "current_step": f"Executed {action_type} on {element_name}.",
                            "pending_question": None,
                            "human_approval": None,
                            "is_security_pause": False # Reset the flag
                        }
                    else:
                        self._add_to_session_log("kinetic", "ERROR: Kinetic registration failed. Recalibrating logic...")

                # Post-click navigation enforcement: if intent was PAY_BILL but page contains 'gold', recover
                # Legacy "Gold" detection removed to allow pure VLM autonomy.
                pass

        if action_type == "FINISHED":
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
            "human_approval": state.get("human_approval"), # REMOVED DEFAULT "approved"
            "is_security_pause": state.get("is_security_pause", False)
        }

    async def _node_wait_for_user(self, state: AgentState) -> Dict[str, Any]:
        """Breakpoint node for manual intervention (Concise Pause handling)."""
        approval = state.get("human_approval")
        if approval == "rejected":
            self._add_to_session_log("security", "🚫 Task rejected by user. Terminating current session.")
            return {
                "current_step": "TASK ABORTED", 
                "browser_context": {"action_type": "FINISHED"},
                "human_approval": "rejected"
            }
        
        return {"current_step": "Authorization received. Resuming...", "human_approval": "approved"}

    def _decide_next_step(self, state: AgentState) -> Literal["continue_loop", "ask_user", "finish_task"]:
        # PRIORITY: Termination on Rejection
        if state.get("human_approval") == "rejected":
            return "finish_task"

        # PRIORITY: Concise Pause for Security or Lock
        if state.get("is_security_pause") or self.security_locked:
            return "ask_user"

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