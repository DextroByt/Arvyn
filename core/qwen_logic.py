import os
import json
import logging
import asyncio
import re
import torch
from PIL import Image
from io import BytesIO
import base64
from typing import Optional, Dict, Any, List, Union
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info

# Import speed-optimized constants from config
from config import (
    QWEN_MODEL_NAME, DEVICE, TORCH_DTYPE, USE_4BIT_QUANTIZATION, 
    MAX_NEW_TOKENS_PARSE, MAX_NEW_TOKENS_ACTION, logger
)
from core.state_schema import IntentOutput

class QwenBrain:
    """
    Superior Visual-Reasoning Engine for Agent Arvyn (Qwen2.5-VL Edition).
    v4.1 OPTIMIZED: High-speed 4-bit quantization for RTX 2050/3050.
    MAINTAINED: Full Autonomy, Coordinate Precision, and Data Integrity.
    """
    
    def __init__(self, model_name: str = QWEN_MODEL_NAME):
        self.model_name = model_name
        self.device = DEVICE
        
        # SPEED UP: Use float16 as the compute dtype for entry-level RTX cards
        self.compute_dtype = torch.float16 if TORCH_DTYPE == "fp16" else torch.bfloat16
        
        logger.info(f"[BRAIN] Booting Engine: {self.model_name} on {self.device}")

        # 1. MEMORY OPTIMIZATION: Setup 4-Bit Quantization for limited VRAM (RTX 2050)
        bnb_config = None
        if USE_4BIT_QUANTIZATION and self.device == "cuda":
            logger.info("[BRAIN] Enabling 4-Bit NF4 Quantization for maximum inference speed.")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=self.compute_dtype
            )

        # 2. INFERENCE OPTIMIZATION: Load with SDPA (Scaled Dot Product Attention)
        # device_map="auto" ensures the model is balanced across available VRAM
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_name,
            torch_dtype=self.compute_dtype,
            quantization_config=bnb_config,
            device_map="auto" if self.device == "cuda" else None,
            attn_implementation="sdpa", # Native PyTorch speed boost
            trust_remote_code=True
        ).eval()
        
        # 3. VISION OPTIMIZATION: Cap visual resolution to reduce token overhead
        # Resizes screenshots to a sweet spot (between 256 and 1024 patches) for banking UIs
        self.processor = AutoProcessor.from_pretrained(
            self.model_name,
            min_pixels=256*28*28,
            max_pixels=1024*28*28 
        )
        logger.info("[BRAIN] Intelligence Engine active with VRAM-safe optimization.")

    def _clean_json_response(self, raw_text: Any) -> str:
        """Robust JSON extraction with multi-layer fallback for VLM outputs."""
        try:
            if not isinstance(raw_text, str):
                raw_text = str(raw_text) if raw_text else "{}"
            
            # Remove whitespace and markdown blocks
            if not raw_text.strip():
                return "{}"

            clean_text = re.sub(r"```json\s*|\s*```", "", raw_text).strip()
            
            # Find the first opening brace and last closing brace
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            if start != -1 and end != -1:
                return clean_text[start:end+1]
            return clean_text
        except Exception as e:
            logger.error(f"[ERROR] Logic Layer: JSON Recovery failed: {e}")
            return "{}"

    def _execute_vlm(self, prompt: str, image_data: Optional[str] = None, max_tokens: int = 1024):
        """
        Internal VLM inference engine.
        Now optimized with use_cache and fixed token limits for high speed.
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ],
                }
            ]

            if image_data:
                image_bytes = base64.b64decode(image_data)
                img = Image.open(BytesIO(image_bytes)).convert("RGB")
                messages[0]["content"].insert(0, {"type": "image", "image": img})

            # Process multimodal inputs
            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to(self.device)

            # 4. SPEED UP: Generation with caching and deterministic parameters
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.01,
                    do_sample=False,
                    use_cache=True # Faster sequential token generation
                )
            
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]
            
            return output_text

        except Exception as e:
            logger.error(f"[FATAL] VLM Inference Error: {e}")
            return "" 

    async def _call_with_retry(self, prompt: str, image_data: Optional[str] = None, max_tokens: int = 1024):
        """Advanced execution wrapper using thread delegation and optimized retries."""
        for attempt in range(2): # Faster failure recovery for autonomous flow
            try:
                response_text = await asyncio.to_thread(self._execute_vlm, prompt, image_data, max_tokens)
                if not response_text:
                    raise ValueError("Empty response from local VLM.")
                return response_text
            except Exception as e:
                logger.warning(f"[RETRY] Brain attempt {attempt+1} failed: {e}")
                if attempt == 1: raise e
                await asyncio.sleep(0.5)

    async def parse_intent(self, user_input: str) -> IntentOutput:
        """Superior Autonomous Intent Extraction at high speed."""
        prompt = f"""
        TASK: High-Precision Intent Parsing for Autonomous Banking.
        USER COMMAND: "{user_input}"
        CONTEXT: Rio Finance Bank (https://roshan-chaudhary13.github.io/rio_finance_bank/)
        
        RULES: Return ONLY raw JSON. Default to Rio Finance Bank for banking keywords.
        
        RETURN JSON:
        {{
            "action": "PAY_BILL | BUY_GOLD | UPDATE_PROFILE | LOGIN | NAVIGATE | SEARCH | QUERY",
            "target": "BANKING",
            "provider": "Rio Finance Bank",
            "amount": float or null,
            "search_query": "Optimized query string",
            "urgency": "HIGH",
            "reasoning": "Direct intent extraction."
        }}
        """
        try:
            # SPEED: Use small token cap for simple text-only parsing
            raw_response = await self._call_with_retry(prompt, max_tokens=MAX_NEW_TOKENS_PARSE)
            clean_json = self._clean_json_response(raw_response)
            data = json.loads(clean_json)
            return IntentOutput(**data)
        except Exception as e:
            logger.error(f"[ERROR] Intent Parser Fault: {e}")
            return IntentOutput(action="NAVIGATE", provider="Rio Finance Bank", target="BANKING", reasoning="Recovery mode.")

    async def analyze_page_for_action(
        self, 
        screenshot_b64: str, 
        goal: str, 
        history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Autonomous Visual Execution Planner powered by Qwen2.5-VL.
        FIXED: Removed user interrogation paths. The agent must solve using USER PROFILE DATA.
        """
        history_log = "\n".join([f"- Step {i}: {h.get('action')} on {h.get('element')} -> {h.get('thought')}" for i, h in enumerate(history[-15:])])
        
        prompt = f"""
        OBJECTIVE: {goal}
        USER PROFILE DATA: {json.dumps(user_context)}

        AUTONOMY RULES:
        1. NO HUMAN INTERVENTION. Use user_context for all PINs, Passwords, and Emails.
        2. DATA MAPPING:
           - Password: user_context['login_credentials']['password']
           - Security PIN: user_context['security_details']['upi_pin'] or 'card_pin'
        3. COORDINATES: Provide [ymin, xmin, ymax, xmax] in 0-1000 scale.

        HISTORY (Last 15 steps):
        {history_log if history else "Initial state."}

        RETURN JSON:
        {{
            "thought": "Direct visual planning based on profile data.",
            "action_type": "CLICK | TYPE | FINISHED",
            "element_name": "Target UI element",
            "coordinates": [ymin, xmin, ymax, xmax],
            "input_text": "Value from profile data",
            "voice_prompt": "Task status update.",
            "is_navigation_required": false
        }}
        """
        try:
            # SPEED: Use the dedicated token limit for complex visual reasoning
            raw_response = await self._call_with_retry(prompt, image_data=screenshot_b64, max_tokens=MAX_NEW_TOKENS_ACTION)
            clean_json = self._clean_json_response(raw_response)
            analysis = json.loads(clean_json)
            
            # Coordinate Validation & Self-Correction
            if analysis.get("action_type") in ["CLICK", "TYPE"]:
                coords = analysis.get("coordinates")
                if not coords or len(coords) != 4:
                     logger.warning("[BRAIN] Unstable coordinates received. Forcing retry.")
                     raise ValueError("Invalid coordinates format.")
            
            return analysis
        except Exception as e:
            logger.error(f"[ERROR] Visual Logic Fault: {e}")
            return {
                "action_type": "CLICK", 
                "element_name": "ERROR_RETRY",
                "coordinates": [0,0,0,0],
                "thought": f"Recovery Attempt due to: {str(e)}"
            }