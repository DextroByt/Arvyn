import json
import logging
import asyncio
import time
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
            self.app = self.workflow.compile(
                checkpointer=checkpointer
            )
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
            
            return {
                "intent": intent_dict, 
                "task_history": [], 
                "current_step": f"Initiating workflow for {provider}..."
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

            # 2) Try to find the specific electricity bill/provider entry
            target_names = [provider_name, 'electricity', 'electricity bill', 'pay electricity', 'pay bill']
            found_entry = False
            for name in target_names:
                try:
                    if await self.browser.find_and_click_text(name):
                        found_entry = True
                        await asyncio.sleep(2.0)
                        break
                except Exception:
                    continue

            if not found_entry:
                # attempt to click a generic 'pay' button
                try:
                    if await self.browser.find_and_click_text('pay'):
                        found_entry = True
                        await asyncio.sleep(2.0)
                except Exception:
                    pass

            if not found_entry:
                return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": "Couldn't locate the bill entry to pay. Shall I try manual steps?"}

            # 3) On the payment page, select a payment method if available
            payment_methods = ['Net Banking', 'Credit Card', 'Debit Card', 'UPI', 'Wallet']
            selected_method = None
            for m in payment_methods:
                try:
                    if await self.browser.select_option_by_text('', m):
                        selected_method = m
                        await asyncio.sleep(1.0)
                        break
                except Exception:
                    continue

            # 4) Attempt to click confirm/pay buttons
            confirm_labels = ['confirm', 'pay now', 'pay', 'proceed to pay']
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

            # 5) Success
            return {"browser_context": {"action_type": "FINISHED"}, "current_step": "Payment completed (automated steps)."}


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
                
                # Dynamic Drift Correction (Maintained as secondary safety layer)
                if count > 0:
                    offset_x = (count * 10) if count % 2 == 0 else -(count * 10)
                    offset_y = (count * 20) if count % 3 == 0 else 0 
                    cx += offset_x
                    cy += offset_y
                    self._add_to_session_log("kinetic", f"Applying drift offset {count} to improve DOM search...")
                
                self.interaction_attempts[interaction_key] = count + 1
                self._add_to_session_log("kinetic", f"Executing Hardened Interaction on '{element_name}'...")
                
                # v5.1 HARDENED CALL: Browser now performs direct DOM click if possible
                # Special-case: if element looks like login/email field, attempt robust autofill first
                if 'email' in element_name.lower() or 'user' in element_name.lower():
                    creds = self.profile.get_provider_credentials(provider_name)
                    if creds:
                        filled = await self.browser.fill_login_fields(creds)
                        # If autofill succeeded for email and password, mark success and continue
                        if filled.get('email'):
                            self._add_to_session_log('kinetic', 'Autofilled login fields from profile.')
                            success = True
                        else:
                            # fallback to clicking at coords
                            success = await self.browser.click_at_coordinates(cx, cy, element_hint=element_name)
                    else:
                        success = await self.browser.click_at_coordinates(cx, cy, element_hint=element_name)
                else:
                    success = await self.browser.click_at_coordinates(cx, cy, element_hint=element_name)
                if success:
                    if action_type == "TYPE":
                        self._add_to_session_log("kinetic", "Inputting secured sequence...")
                        # Prefer profile credentials for login-related fields to avoid LLM hallucinated values
                        ename = element_name.lower()
                        creds = self.profile.get_provider_credentials(provider_name)
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
                            preferred = creds.get('password')
                            if preferred:
                                await self.browser.type_text(preferred)
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