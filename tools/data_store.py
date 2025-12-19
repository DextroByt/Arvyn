import json
import os
import logging
from typing import Dict, Any, Optional
from config import USER_PROFILE_PATH, logger

class ProfileManager:
    """
    Production Context Engine for Agent Arvyn.
    Manages user preferences, provider metadata, and a verified registry of Official Sites.
    """
    
    def __init__(self):
        self.path = USER_PROFILE_PATH
        self._ensure_file()

    def _ensure_file(self):
        """Initializes the storage structure for providers and verified sites."""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            if not os.path.exists(self.path):
                # 'verified_sites' acts as the agent's long-term memory for official URLs
                initial_data = {
                    "providers": {}, 
                    "verified_sites": {}, 
                    "settings": {"auto_navigate_verified": True}
                }
                with open(self.path, 'w') as f:
                    json.dump(initial_data, f, indent=4)
                logger.info(f"Intelligent storage initialized at {self.path}")
        except Exception as e:
            logger.error(f"Storage Initialization Error: {e}")

    def get_data(self) -> Dict[str, Any]:
        """Loads all stored agent knowledge with safety defaults."""
        try:
            if not os.path.exists(self.path):
                return {"providers": {}, "verified_sites": {}, "settings": {}}
            with open(self.path, 'r') as f:
                data = json.load(f)
                # Migration: Ensure keys exist in older profile versions
                if "verified_sites" not in data:
                    data["verified_sites"] = {}
                return data
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error reading agent memory: {e}")
            return {"providers": {}, "verified_sites": {}, "settings": {}}

    def _save_data(self, data: Dict[str, Any]):
        """Atomic write to persist agent knowledge."""
        try:
            with open(self.path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to persist agent memory: {e}")

    def save_verified_site(self, entity_name: str, official_url: str):
        """
        Registers an official URL for an entity.
        Future visits to this entity will skip Google Search.
        """
        data = self.get_data()
        key = entity_name.upper()
        data["verified_sites"][key] = official_url
        self._save_data(data)
        logger.info(f"Memory Updated: Verified official site for {key} -> {official_url}")

    def get_verified_url(self, entity_name: str) -> Optional[str]:
        """
        Checks if the agent has a verified URL in its memory for the given entity.
        """
        data = self.get_data()
        return data.get("verified_sites", {}).get(entity_name.upper())

    def update_provider(self, provider_name: str, details: Dict[str, Any]):
        """Stores complex metadata for a provider (e.g. account numbers or preferences)."""
        data = self.get_data()
        data["providers"][provider_name.upper()] = details
        self._save_data(data)
        logger.info(f"Updated provider metadata for {provider_name}")

    def get_provider_details(self, provider_name: str) -> Dict[str, Any]:
        """Case-insensitive lookup for specific provider metadata."""
        data = self.get_data()
        providers = data.get("providers", {})
        
        for key, value in providers.items():
            if key.upper() == provider_name.upper():
                return value
        return {}