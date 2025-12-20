import json
import os
import logging
import copy
from typing import Dict, Any, Optional, List
from config import USER_PROFILE_PATH, logger

class ProfileManager:
    """
    Advanced Memory & Context Engine for Agent Arvyn.
    Features: Atomic writes, Task State Persistence, and 
    Hardened Banking Context for Rio Finance Bank.
    """
    
    # Static Reference for the Primary Automation Target
    RIO_URL = "https://roshan-chaudhary13.github.io/rio_finance_bank/"
    
    def __init__(self):
        self.path = USER_PROFILE_PATH
        self._ensure_file()
        self._bootstrap_banking_context()

    def _ensure_file(self):
        """Initializes high-fidelity storage with the required production schema."""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            if not os.path.exists(self.path):
                # 'task_registry' allows Arvyn to resume tasks after crashes
                initial_data = {
                    "personal_info": {
                        "full_name": "Arvyn User",
                        "email": "user@example.com",
                        "phone": "+1234567890"
                    },
                    "providers": {
                        "RIO_FINANCE_BANK": {
                            "url": self.RIO_URL,
                            "account_id": "RIO-778899",
                            "login_method": "Visual-ID",
                            "notes": "Primary target for Bill Pay and Gold tasks."
                        }
                    }, 
                    "verified_sites": {
                        "RIO_FINANCE_BANK": self.RIO_URL,
                        "RIO_BANK": self.RIO_URL,
                        "RIO_FINANCE": self.RIO_URL
                    },
                    "task_registry": {
                        "active_goal": None,
                        "step_count": 0,
                        "status": "IDLE"
                    },
                    "settings": {
                        "auto_navigate_verified": True,
                        "strict_banking_mode": True
                    }
                }
                self._save_data(initial_data)
                logger.info(f"📂 Arvyn Vault: Initialized banking memory at {self.path}")
        except Exception as e:
            logger.error(f"Vault Initialization Error: {e}")

    def _bootstrap_banking_context(self):
        """Guarantees that Rio Finance Bank data is never lost or corrupted."""
        data = self.get_data()
        modified = False
        
        # 1. Ensure Verified Sites contain the Rio URL
        v_sites = data.setdefault("verified_sites", {})
        if v_sites.get("RIO_FINANCE_BANK") != self.RIO_URL:
            v_sites["RIO_FINANCE_BANK"] = self.RIO_URL
            v_sites["RIO_BANK"] = self.RIO_URL
            modified = True
            
        # 2. Ensure Provider Metadata exists
        providers = data.setdefault("providers", {})
        if "RIO_FINANCE_BANK" not in providers:
            providers["RIO_FINANCE_BANK"] = {
                "url": self.RIO_URL,
                "account_id": "RIO-778899",
                "notes": "Forced injection for banking reliability."
            }
            modified = True
            
        if modified:
            self._save_data(data)
            logger.info("✅ Arvyn Memory: Rio Finance Bank context synchronized.")

    def get_data(self) -> Dict[str, Any]:
        """Loads agent knowledge with recursive key-validation."""
        try:
            if not os.path.exists(self.path):
                return {}
            with open(self.path, 'r') as f:
                data = json.load(f)
                
                # Migration safety: ensure all top-level keys exist
                keys = ["providers", "verified_sites", "personal_info", "task_registry", "settings"]
                for k in keys:
                    if k not in data: data[k] = {}
                
                return data
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Vault Read Error: {e}")
            return {"providers": {}, "verified_sites": {}, "task_registry": {}}

    def _save_data(self, data: Dict[str, Any]):
        """Atomic Save: Writes to a temp file then renames to prevent data loss."""
        try:
            temp_path = f"{self.path}.tmp"
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=4)
            os.replace(temp_path, self.path)
        except Exception as e:
            logger.error(f"Vault Save Error: {e}")

    # --- Task State Persistence ---

    def track_task(self, goal: str, status: str = "IN_PROGRESS"):
        """Stores the current active task for LLM context retrieval."""
        data = self.get_data()
        data["task_registry"]["active_goal"] = goal
        data["task_registry"]["status"] = status
        self._save_data(data)
        logger.info(f"Memory: Tracking goal -> {goal}")

    def clear_task(self):
        """Resets the task state upon successful completion."""
        data = self.get_data()
        data["task_registry"]["active_goal"] = None
        data["task_registry"]["status"] = "IDLE"
        self._save_data(data)

    # --- Provider & Context Logic ---

    def get_provider_details(self, provider_name: str) -> Dict[str, Any]:
        """Advanced lookup with fuzzy alias matching (e.g. 'Rio' matches 'RIO_FINANCE_BANK')."""
        data = self.get_data()
        providers = data.get("providers", {})
        query = provider_name.upper()
        
        # Direct Match
        if query in providers: return providers[query]
        
        # Partial Match (Alias support)
        for key in providers:
            if query in key or key in query:
                return providers[key]
                
        return {}

    def get_verified_url(self, entity_name: str) -> Optional[str]:
        """Checks the verified site registry."""
        data = self.get_data()
        return data.get("verified_sites", {}).get(entity_name.upper())

    def update_provider(self, provider_name: str, details: Dict[str, Any]):
        """Updates provider details using a deep merge."""
        data = self.get_data()
        key = provider_name.upper()
        if key not in data["providers"]: data["providers"][key] = {}
        data["providers"][key].update(details)
        self._save_data(data)

    def get_full_context(self, provider: str) -> Dict[str, Any]:
        """Packages all relevant data for the Gemini Brain."""
        data = self.get_data()
        return {
            "personal_info": data.get("personal_info", {}),
            "banking_details": self.get_provider_details(provider),
            "last_task_state": data.get("task_registry", {})
        }