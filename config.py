import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --- Logging Configuration ---
# Configured for high-visibility production logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("arvyn_session.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ArvynConfig")

class Config:
    """
    Central configuration for Agent Arvyn.
    Optimized for Gemini 2.5 and Intelligent Discovery loops.
    """
    
    # AI Model Settings
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # Defaulting to the powerful 2.5-flash for speed and reasoning
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    
    # Browser Settings
    # Headless mode is disabled by default to allow visual search monitoring
    HEADLESS = os.getenv("HEADLESS_MODE", "False").lower() == "true"
    BROWSER_TYPE = "playwright"
    SCREENSHOT_PATH = "screenshots"
    
    # Data Storage
    USER_PROFILE_PATH = "data/user_profile.json"
    
    # Voice & Mic Settings
    DEFAULT_VOICE_ID = None  
    # Timeout for automatic silence detection (if fallback is used)
    COMMAND_TIMEOUT = 10     
    
    # UI Settings (Glass Morphism Defaults)
    THEME = "GlassMorphism"
    ORB_COLOR = "#00d2ff"
    ACCENT_COLOR = "#00d2ff"
    ORB_SIZE = 80
    DASHBOARD_SIZE = (400, 500)
    
    @classmethod
    def validate(cls):
        """Validates system health and ensures critical paths exist."""
        if not cls.GEMINI_API_KEY:
            logger.error("CRITICAL: GEMINI_API_KEY is missing. Check your .env file.")
            return False
            
        os.makedirs(cls.SCREENSHOT_PATH, exist_ok=True)
        os.makedirs(os.path.dirname(cls.USER_PROFILE_PATH), exist_ok=True)
            
        return True

# Constants for direct import to maintain compatibility with existing tools
ORB_SIZE = Config.ORB_SIZE
DASHBOARD_SIZE = Config.DASHBOARD_SIZE
ACCENT_COLOR = Config.ACCENT_COLOR
GEMINI_API_KEY = Config.GEMINI_API_KEY
GEMINI_MODEL_NAME = Config.GEMINI_MODEL_NAME
SCREENSHOT_PATH = Config.SCREENSHOT_PATH
USER_PROFILE_PATH = Config.USER_PROFILE_PATH
DEFAULT_VOICE_ID = Config.DEFAULT_VOICE_ID
COMMAND_TIMEOUT = Config.COMMAND_TIMEOUT

# Automatic validation on module import
Config.validate()