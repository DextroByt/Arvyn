import json
import os
import logging
import copy
from typing import Dict, Any, Optional, List
from config import USER_PROFILE_PATH, logger

class ProfileManager:
    """
    Advanced Memory & Context Engine for Agent Arvyn.
    UPGRADED: Features Multi-Site Context Resolution and Strict Autonomy.
    FIXED: Removed forced Rio Bank redirection for general site requests.
    IMPROVED: Atomic storage logic with task-state persistence.
    """
    
    def __init__(self):
        self.path = USER_PROFILE_PATH
        self._ensure_file()
        self._bootstrap_banking_context()

    def _ensure_file(self):
        """Initializes high-fidelity storage with the required production schema."""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            if not os.path.exists(self.path):
                # IMPROVEMENT: Default initial data is now a clean schema.
                initial_data = {
                    "personal_info": {
                        "full_name": "Arvyn User",
                        "email": "user@example.com",
                        "phone": "+1234567890",
                        "upi id": "user@okrio"
                    },
                    "providers": {}, 
                    "verified_sites": {
                        "GOOGLE": "https://www.google.com",
                        "GITHUB": "https://github.com"
                    },
                    "task_registry": {
                        "active_goal": None,
                        "step_count": 0,
                        "status": "IDLE"
                    },
                    "settings": {
                        "auto_navigate_verified": True,
                        "strict_banking_mode": True,
                        "require_approval_for_payments": False
                    }
                }
                self._save_data(initial_data)
                logger.info(f"📂 Arvyn Vault: Initialized clean memory at {self.path}")
        except Exception as e:
            logger.error(f"Vault Initialization Error: {e}")

    def _bootstrap_banking_context(self):
        """
        Ensures the data structure is consistent without polluting it.
        FIXED: No longer injects RIO_URL into generic 'BANK' keywords.
        """
        data = self.get_data()
        modified = False
        
        # Ensure top-level structure exists for autonomy
        keys = ["providers", "verified_sites", "personal_info", "task_registry", "settings"]
        for k in keys:
            if k not in data:
                data[k] = {}
                modified = True
            
        if modified:
            self._save_data(data)
            logger.info("✅ Arvyn Memory: Context schema synchronized for autonomous operation.")

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
        """
        Advanced lookup from user_profile.json.
        IMPROVED: Prioritizes exact matches for security.
        """
        data = self.get_data()
        providers = data.get("providers", {})
        query = provider_name.upper().replace(" ", "_")
        
        # 1. Direct Match (e.g. RIO_FINANCE_BANK)
        if query in providers: return providers[query]
        
        # 2. Key-in-Query Match (e.g. "Rio Bank" matches "RIO_FINANCE_BANK")
        for key in providers:
            if key in query:
                return providers[key]
                
        # 3. Query-in-Key Match
        for key in providers:
            if query in key:
                return providers[key]
                
        return {}

    def get_provider_credentials(self, provider_name: str) -> Dict[str, Any]:
        """Return stored login credentials for a provider, or empty dict."""
        details = self.get_provider_details(provider_name)
        creds = details.get('login_credentials', {}) if isinstance(details, dict) else {}
        return creds if isinstance(creds, dict) else {}

    def get_verified_url(self, entity_name: str) -> Optional[str]:
        """
        Checks the verified site registry.
        FIXED: Ensures Flipkart/Amazon requests pull from profile, not defaults.
        """
        data = self.get_data()
        verified = data.get("verified_sites", {})
        query = entity_name.upper().replace(" ", "_")
        
        return verified.get(query)

    def update_provider(self, provider_name: str, details: Dict[str, Any]):
        """Updates provider details using a deep merge."""
        data = self.get_data()
        key = provider_name.upper().replace(" ", "_")
        if key not in data["providers"]: data["providers"][key] = {}
        data["providers"][key].update(details)
        self._save_data(data)

    def get_full_context(self, provider: str) -> Dict[str, Any]:
        """
        Packages all relevant data for the Gemini Brain.
        IMPROVED: Explicitly includes security credentials for autonomous login/PIN entry.
        """
        data = self.get_data()
        provider_details = self.get_provider_details(provider)
        
        return {
            "personal_info": data.get("personal_info", {}),
            "login_credentials": provider_details.get("login_credentials", {}),
            "security_details": provider_details.get("security_details", {}),
            "account_metadata": provider_details.get("account_metadata", {}),
            "last_task_state": data.get("task_registry", {})
        }