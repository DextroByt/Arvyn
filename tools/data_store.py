import json
import os
from typing import Any, Dict, List, Optional
from threading import Lock
from config import USER_PROFILE_PATH

class ArvynDataStore:
    def __init__(self):
        """Initializes the data store and ensures the profile exists [cite: 217-218]."""
        self.file_path = USER_PROFILE_PATH
        self.lock = Lock()  # Ensures thread-safe writes from different GUI/Agent threads
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Creates an empty profile if it does not exist ."""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({"personal_info": {}, "providers": {}}, f, indent=4)

    def get_profile(self) -> Dict[str, Any]:
        """Reads the entire profile with thread safety."""
        with self.lock:
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {"personal_info": {}, "providers": {}}

    def update_field(self, category: str, key: str, value: Any):
        """Updates a specific field and saves to disk immediately[cite: 138, 218]."""
        with self.lock:
            data = self.get_profile()
            if category not in data:
                data[category] = {}
            data[category][key] = value
            
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=4)

    def get_missing_fields(self, provider_name: str, required_fields: List[str]) -> List[str]:
        """
        Performs Gap Analysis to identify what the agent needs to ask the user[cite: 130].
        This is core to the 'Cyclic Data Validation' workflow[cite: 125].
        """
        profile = self.get_profile()
        provider_data = profile.get("providers", {}).get(provider_name, {})
        personal_info = profile.get("personal_info", {})
        
        missing = []
        for field in required_fields:
            # Check both provider-specific data and general personal info
            if field not in provider_data and field not in personal_info:
                missing.append(field)
        return missing

    def clear_cache(self):
        """Resets the data store (for privacy or debugging)."""
        with self.lock:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
            self._ensure_file_exists()