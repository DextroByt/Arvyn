import json
import os
import logging
from typing import Dict, Any, Optional
from config import USER_PROFILE_PATH, logger

class ProfileManager:
    """
    Handles the storage and retrieval of user-specific context and metadata.
    Simplified for the prototype to support direct command execution.
    """
    
    def __init__(self):
        self.path = USER_PROFILE_PATH
        self._ensure_file()

    def _ensure_file(self):
        """Initializes the storage file and directory structure if missing."""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            if not os.path.exists(self.path):
                with open(self.path, 'w') as f:
                    json.dump({"providers": {}, "settings": {}}, f, indent=4)
                logger.info(f"Context storage initialized at {self.path}")
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")

    def get_data(self) -> Dict[str, Any]:
        """Loads the profile data with error safety."""
        try:
            if not os.path.exists(self.path):
                return {"providers": {}, "settings": {}}
            with open(self.path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error reading storage file: {e}")
            return {"providers": {}, "settings": {}}

    def update_provider(self, provider_name: str, details: Dict[str, Any]):
        """Saves or updates information for a specific provider."""
        data = self.get_data()
        data["providers"][provider_name.upper()] = details
        
        try:
            with open(self.path, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Updated context for {provider_name}")
        except Exception as e:
            logger.error(f"Failed to save update: {e}")

    def get_provider_details(self, provider_name: str) -> Dict[str, Any]:
        """
        Retrieves stored context for a provider using case-insensitive lookup.
        Returns an empty dict if no data exists.
        """
        data = self.get_data()
        providers = data.get("providers", {})
        
        # Robust case-insensitive search
        for key, value in providers.items():
            if key.upper() == provider_name.upper():
                return value
                
        return {}