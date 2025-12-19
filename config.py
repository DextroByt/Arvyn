import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Logging Configuration ---
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
    """Central configuration for Agent Arvyn."""
    
    # AI Model Settings - Updated for Gemini 2.5
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    
    # Browser Settings
    HEADLESS = os.getenv("HEADLESS_MODE", "False").lower() == "true"
    BROWSER_TYPE = "playwright"
    SCREENSHOT_PATH = "screenshots"
    
    # Data Storage
    USER_PROFILE_PATH = "data/user_profile.json"
    
    # Voice Settings
    DEFAULT_VOICE_ID = None  # Uses system default
    COMMAND_TIMEOUT = 5      # Seconds to wait for audio
    
    # UI Settings
    THEME = "GlassMorphism"
    ORB_COLOR = "#00d2ff"
    ACCENT_COLOR = "#00d2ff"
    ORB_SIZE = 80
    DASHBOARD_SIZE = (400, 500)
    
    @classmethod
    def validate(cls):
        """Validate critical configuration and initialize folders."""
        if not cls.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not found in environment variables.")
            return False
            
        os.makedirs(cls.SCREENSHOT_PATH, exist_ok=True)
        os.makedirs(os.path.dirname(cls.USER_PROFILE_PATH), exist_ok=True)
            
        return True

# Constants for direct import
ORB_SIZE = Config.ORB_SIZE
DASHBOARD_SIZE = Config.DASHBOARD_SIZE
ACCENT_COLOR = Config.ACCENT_COLOR
GEMINI_API_KEY = Config.GEMINI_API_KEY
GEMINI_MODEL_NAME = Config.GEMINI_MODEL_NAME
SCREENSHOT_PATH = Config.SCREENSHOT_PATH
USER_PROFILE_PATH = Config.USER_PROFILE_PATH
DEFAULT_VOICE_ID = Config.DEFAULT_VOICE_ID
COMMAND_TIMEOUT = Config.COMMAND_TIMEOUT

# Validate on import
Config.validate()