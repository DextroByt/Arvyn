import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Union, Literal, Optional
from langgraph.graph import StateGraph, END

# Use high-fidelity exports from upgraded config
from config import (
    logger, 
    GEMINI_MODEL_NAME, 
    VIEWPORT_WIDTH, 
    VIEWPORT_HEIGHT,
    DASHBOARD_SIZE
)
from core.state_schema import AgentState
from core.gemini_logic import GeminiBrain
from tools.browser import ArvynBrowser
from tools.data_store import ProfileManager
from tools.voice import ArvynVoice

class ArvynOrchestrator:
    """
    Superior Autonomous Orchestrator for Agent Arvyn.
    UPGRADED: Features Kinetic Anti-Loop logic, Dynamic Offset Scaling, and Intelligent Provider Routing.
    FIXED: Resolves click-unresponsiveness on Rio Bank and ensures data integrity.
    IMPROVED: Properly routes to different platforms (Flipkart, Amazon, etc.) based on user intent.
    """

    def __init__(self, model_name: str = GEMINI_MODEL_NAME):
        self.brain = GeminiBrain(model_name=model_name)
        self.browser = ArvynBrowser(headless=False)
        self.profile = ProfileManager()
        self.voice = ArvynVoice()
        self.app = None
        self.workflow = self._create_workflow()
        
        self.session_log = []
        # Track repeated element interactions to apply scaling offsets
        self.interaction_attempts = {} 
        
        logger.info(f"🚀 Arvyn Core v3.6: Orchestrator active. Anti-Loop Engine engaged.")

    async def init_app(self, checkpointer):
        """Compiles the LangGraph with Persistent Checkpointing and PIN-only HITL."""
        if self.app is None:
            self.app = self.workflow.compile(
                checkpointer=checkpointer,
                interrupt_before=["human_interaction_node"]
            )
            logger.info("✅ Arvyn Autonomous Core: Logic layers compiled.")

    async def cleanup(self):
        """Graceful release of browser and kinetic resources."""
        if self.browser:
            self._add_to_session_log("system", "Deactivating kinetic layer...")
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
            action = intent_dict.get('action', 'QUERY')
            target = intent_dict.get('target', 'BANKING')
            
            self._add_to_session_log("intent_parser", f"Intent: {action} | Provider: {provider} | Target: {target}")
            
            return {
                "intent": intent_dict, 
                "task_history": [], 
                "current_step": f"Initiating {action} workflow for {provider}..."
            }
        except Exception as e:
            logger.error(f"Intent Extraction Failure: {e}")
            return {"current_step": "Clarification required.", "intent": None}

    def _resolve_target_url(self, provider_name: str) -> str:
        """
        Enhanced URL Resolution: Maps providers to their actual URLs.
        IMPROVED: Now properly routes to different platforms based on intent.
        """
        # Banking-specific URLs (Rio Finance Bank)
        if any(key in provider_name.lower() for key in ["rio", "finance", "bank", "gold", "bill"]):
            return "https://roshan-chaudhary13.github.io/rio_finance_bank/"
        
        # Shopping platforms
        if "flipkart" in provider_name.lower():
            return "https://www.flipkart.com/"
        if "amazon" in provider_name.lower():
            return "https://www.amazon.com/"
        
        # Entertainment platforms
        if "netflix" in provider_name.lower():
            return "https://www.netflix.com/in/"
        
        # Developer/Other platforms
        if "github" in provider_name.lower():
            return "https://github.com/"
        
        # Jio Financial Services
        if "jio" in provider_name.lower():
            return "https://www.jiofinance.com/"
        
        # BSNL (telecom)
        if "bsnl" in provider_name.lower():
            return "https://www.bsnl.co.in/"
        
        # Fallback: Try to get from profile manager
        norm_name = provider_name.upper().replace(" ", "_")
        url = self.profile.get_verified_url(norm_name)
        
        if url:
            return url
        
        # Final fallback: Search for the provider
        return f"https://www.google.com/search?q={provider_name}+official+site"

    async def _node_site_discovery(self, state: AgentState) -> Dict[str, Any]:
        """Navigates and prepares for the Auto-Login Check."""
        intent = state.get("intent") or {}
        provider = intent.get("provider", "Rio Finance Bank")
        action = intent.get("action", "QUERY")
        target_url = self._resolve_target_url(provider)

        try:
            page = await self.browser.ensure_page()
            
            # Only navigate if we're not already at the target URL
            if target_url not in page.url or page.url == "about:blank":
                self._add_to_session_log("discovery", f"Navigating to: {provider} ({target_url})")
                await self.browser.navigate(target_url)
                await asyncio.sleep(4.0) # Buffer for heavy React hydration
            else:
                self._add_to_session_log("discovery", f"Already at {provider}. Proceeding...")
            
            self._add_to_session_log("security", "STATUS: Verifying Login/Session state...")
            return {"current_step": f"Connection secured to {provider}. Checking login status..."}
            
        except Exception as e:
            self._add_to_session_log("error", f"Portal connection error: {str(e)}")
            return {"current_step": "Discovery retry required..."}

    async def _node_autonomous_executor(self, state: AgentState) -> Dict[str, Any]:
        """
        Main autonomous loop.
        UPGRADED: Uses Interaction Counters and Scaled Offsets for Click Reliability.
        PRESERVED: All credential handling, security features, and anti-loop logic.
        """
        self._add_to_session_log("executor", "Observing UI state...")
        
        intent = state.get("intent")
        history = state.get("task_history", [])
        approval = state.get("human_approval")
        cached_analysis = state.get("browser_context", {})

        if not intent:
            return {"browser_context": {"action_type": "ASK_USER"}, "pending_question": "I've lost the objective."}

        # Resumption logic for PIN authorization
        if approval == "approved" and cached_analysis.get("action_type") in ["CLICK", "TYPE"]:
            self._add_to_session_log("security", "PIN Authorized. Resuming sensitive sequence...")
            analysis = cached_analysis
        else:
            screenshot = await self.browser.get_screenshot_b64()
            provider_name = intent.get("provider", "Rio Finance Bank")
            action = intent.get("action", "QUERY")
            
            # IMPROVEMENT: Goal explicitly forbids hallucination and emphasizes STEP 0
            goal = (
                f"STEP 0: If 'Login' or 'Sign In' is visible, LOGIN FIRST using user_context['login_credentials']. "
                f"STEP 1: Only once logged in, perform {action} on {provider_name}. "
                f"CRITICAL: USE EXACT DATA. Do NOT use 'password123' if the data says 'admin123'."
            )
            
            user_context = self.profile.get_provider_details(provider_name)
            user_context.update(self.profile.get_data().get("personal_info", {}))

            self._add_to_session_log("brain", "Analyzing page for kinetic action...")
            analysis = await self.brain.analyze_page_for_action(screenshot, goal, history, user_context)

        action_type = analysis.get("action_type")
        current_history = history.copy()
        element_name = analysis.get("element_name", "").lower()
        input_text = analysis.get("input_text", "")

        # HITL: Only "pin" triggers user authorization.
        is_pin_field = any(k in element_name for k in ["pin", "upi", "card pin", "security pin"])
        
        if action_type == "TYPE" and is_pin_field and approval != "approved":
            self._add_to_session_log("security", f"AUTH REQUIRED: Secure Payment PIN field.")
            return {
                "browser_context": analysis,
                "pending_question": f"Authorization Required: I need your {element_name} to complete this payment.",
                "current_step": f"LOCKED: Awaiting PIN authorization."
            }

        # KINETIC EXECUTION WITH ANTI-LOOP LOGIC
        if action_type in ["CLICK", "TYPE"]:
            coords = analysis.get("coordinates")
            if coords and len(coords) == 4:
                ymin, xmin, ymax, xmax = coords
                cx = int(((xmin + xmax) / 2) * (VIEWPORT_WIDTH / 1000))
                cy = int(((ymin + ymax) / 2) * (VIEWPORT_HEIGHT / 1000))
                
                # --- KINETIC ANTI-LOOP: Detect and Offset repeated clicks ---
                interaction_key = f"{action_type}_{element_name}"
                count = self.interaction_attempts.get(interaction_key, 0)
                
                if count > 0:
                    # Apply a scaled offset to try hitting different parts of the button area
                    offset = (count * 6) if count % 2 == 0 else -(count * 6)
                    self._add_to_session_log("kinetic", f"RETRY: Applying interaction offset of {offset}px to bypass UI blocker.")
                    cx += offset
                    cy += offset
                
                self.interaction_attempts[interaction_key] = count + 1

                self._add_to_session_log("kinetic", f"Executing interaction on {analysis.get('element_name')}...")
                await self.browser.click_at_coordinates(cx, cy)
                
                if action_type == "TYPE":
                    # Ensure we aren't using the hallucinated password
                    if "password123" in input_text.lower():
                         self._add_to_session_log("error", "CRITICAL: Brain attempted hallucinated password. Intercepting...")
                         input_text = user_context.get("login_credentials", {}).get("password", input_text)
                    
                    self._add_to_session_log("kinetic", f"Autofilling credentials...")
                    await self.browser.type_text(input_text)
                
                await asyncio.sleep(2.8) 
                
                current_history.append({
                    "action": action_type, 
                    "element": analysis.get("element_name"),
                    "thought": analysis.get("thought")
                })
                
                # Reset counters if we navigated or moved to a new element type
                if len(history) > 0 and history[-1].get("element") != analysis.get("element_name"):
                    self.interaction_attempts = {interaction_key: count + 1}

        elif action_type == "FINISHED":
            self._add_to_session_log("executor", "✅ Task completed successfully.")

        return {
            "screenshot": await self.browser.get_screenshot_b64(),
            "task_history": current_history,
            "browser_context": analysis,
            "current_step": analysis.get("thought", "Advancing autonomous workflow..."),
            "pending_question": analysis.get("voice_prompt") if action_type == "ASK_USER" else None,
            "human_approval": None 
        }

    async def _node_wait_for_user(self, state: AgentState) -> Dict[str, Any]:
        approval = state.get("human_approval")
        if approval == "approved":
            self._add_to_session_log("human_interaction", "Authorization confirmed. Resuming...")
        elif approval == "rejected":
            self._add_to_session_log("human_interaction", "Action rejected by user.")
            return {"current_step": "REJECTED: Task paused."}
        
        return {"current_step": "Awaiting user decision..."}

    def _decide_next_step(self, state: AgentState) -> Literal["continue_loop", "ask_user", "finish_task"]:
        analysis = state.get("browser_context", {})
        action_type = analysis.get("action_type")
        
        if action_type == "FINISHED": return "finish_task"
        if action_type == "ASK_USER" or state.get("pending_question"): return "ask_user"
        
        if len(state.get("task_history", [])) > 45: # Increased limit for complex bill pay flows
            self._add_to_session_log("safety", "Maximum recursion limit reached.")
            return "finish_task"
            
        return "continue_loop"