import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError
from cryptography.fernet import Fernet
import keyring # For Windows Secure Storage

from config import USER_PROFILE_PATH, logger

# ==========================================
# 1. DATA SCHEMA (The "Symbolic" Rules)
# ==========================================
class UserProfile(BaseModel):
    """
    Strict schema for Arvyn's long-term memory.
    """
    user_name: str = "User"
    last_interaction: str = Field(default_factory=lambda: datetime.now().isoformat())
    preferences: Dict[str, Any] = {
        "theme": "dark",
        "voice_enabled": True,
        "headless": False
    }
    financial_targets: Dict[str, str] = {} # e.g., {"Electric": "https://portal.utility.com"}
    encrypted_vault: Dict[str, str] = {} # Encrypted sensitive pointers
    version: str = "1.0.0"

# ==========================================
# 2. SECURE DATA STORE
# ==========================================
class SecureDataStore:
    """
    Handles encrypted persistence for Arvyn.
    Ensures financial data is never stored in plain text.
    """
    def __init__(self):
        self.profile_path = Path(USER_PROFILE_PATH)
        self._fernet: Optional[Fernet] = None
        self._init_encryption()
        self.current_profile: UserProfile = self.load_profile()

    def _init_encryption(self):
        """
        Initializes the AES-256 engine.
        Stores the master key in Windows Credential Manager (Keyring).
        """
        service_id = "AgentArvyn_Vault"
        key = keyring.get_password(service_id, "master_key")

        if not key:
            logger.info("Generating new master encryption key...")
            new_key = Fernet.generate_key().decode()
            keyring.set_password(service_id, "master_key", new_key)
            key = new_key

        self._fernet = Fernet(key.encode())

    def encrypt_value(self, plain_text: str) -> str:
        """Encrypts a string for storage."""
        return self._fernet.encrypt(plain_text.encode()).decode()

    def decrypt_value(self, cipher_text: str) -> str:
        """Decrypts a string for use by the agent."""
        try:
            return self._fernet.decrypt(cipher_text.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return ""

    def load_profile(self) -> UserProfile:
        """Loads and validates the user profile from disk."""
        if not self.profile_path.exists():
            logger.warning("No profile found. Creating a fresh one.")
            new_profile = UserProfile()
            self.save_profile(new_profile)
            return new_profile

        try:
            with open(self.profile_path, "r", encoding='utf-8') as f:
                data = json.load(f)
            return UserProfile(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Profile corruption detected: {e}. Recovering default.")
            return UserProfile()

    def save_profile(self, profile: Optional[UserProfile] = None):
        """
        Performs an ATOMIC write to prevent data loss.
        """
        to_save = profile or self.current_profile
        to_save.last_interaction = datetime.now().isoformat()
        
        temp_path = self.profile_path.with_suffix(".tmp")
        
        try:
            # Write to temporary file first
            with open(temp_path, "w", encoding='utf-8') as f:
                json.dump(to_save.model_dump(), f, indent=4)
            
            # Atomic rename (Windows handles this via os.replace)
            os.replace(temp_path, self.profile_path)
            logger.debug("Profile saved successfully.")
            self.current_profile = to_save
        except Exception as e:
            logger.critical(f"Critical Fail: Could not save data: {e}")
            if temp_path.exists():
                os.remove(temp_path)

    def update_financial_target(self, provider_name: str, url: str):
        """Saves a new automation target (e.g. 'Bank of America')."""
        self.current_profile.financial_targets[provider_name] = url
        self.save_profile()
        logger.info(f"Updated target: {provider_name}")

    def store_sensitive_data(self, key: str, value: str):
        """Safely stores sensitive info in the encrypted vault."""
        encrypted = self.encrypt_value(value)
        self.current_profile.encrypted_vault[key] = encrypted
        self.save_profile()