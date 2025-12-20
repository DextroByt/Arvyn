import os
import logging
import sys
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --- ROBUST LOGGING CONFIGURATION ---
# Fixes UnicodeEncodeError (charmap) on Windows consoles (CMD/PowerShell)
# Ensures high-fidelity UTF-8 logging remains available in the 'arvyn_session.log' file.

class SafeStreamHandler(logging.StreamHandler):
    """A stream handler that falls back to stripping non-ASCII characters if encoding fails."""
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Fallback: Strip emojis/special chars that the console cannot handle natively
            msg = self.format(record)
            self.stream.write(msg.encode('ascii', 'replace').decode('ascii') + self.terminator)
            self.flush()

# Define standard format for all modules
log_format = '%(asctime)s | %(levelname)s | [%(name)s] | %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter(log_format, datefmt=date_format)

# Configure the Root Logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 1. File Handler (Always UTF-8 to keep full logs with emojis for debugging)
file_handler = logging.FileHandler("arvyn_session.log", encoding='utf-8')
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

# 2. Stream Handler (Console output with safety fallback for Windows encoding)
stream_handler = SafeStreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
root_logger.addHandler(stream_handler)

# Specific Config Logger
logger = logging.getLogger("ArvynConfig")

class Config:
    """
    Central configuration for Agent Arvyn.
    Optimized for Gemini 2.5 Flash, High-Resolution Browsing, and Dashboard Visibility.
    """
    
    # --- AI MODEL SETTINGS ---
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Updated to 'gemini-2.5-flash' for superior discovery speed and reasoning.
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    
    # --- KINETIC & BROWSER SETTINGS ---
    # Increased to Full HD (1920x1080) to ensure banking sites display all elements.
    VIEWPORT_WIDTH = 1920
    VIEWPORT_HEIGHT = 1080
    
    HEADLESS = os.getenv("HEADLESS_MODE", "False").lower() == "true"
    BROWSER_TYPE = "playwright"
    SCREENSHOT_PATH = "screenshots"
    
    # --- DATA & MEMORY STORAGE ---
    USER_PROFILE_PATH = "data/user_profile.json"
    LOG_FILE_PATH = "arvyn_session.log"
    
    # --- VOICE & INTERACTION ---
    DEFAULT_VOICE_ID = None  
    STT_ENERGY_THRESHOLD = 300 
    COMMAND_TIMEOUT = 30 # High buffer for heavy banking sites
    
    # --- UI SETTINGS (EXPANDED COMMAND CENTER) ---
    THEME = "GlassMorphism_V2"
    ORB_COLOR = "#00d2ff"
    ACCENT_COLOR = "#00d2ff"
    ERROR_COLOR = "#ff4b2b"
    SUCCESS_COLOR = "#2ecc71"
    
    ORB_SIZE = 85
    # Dashboard size expanded to comfortably show the high-resolution site feed.
    DASHBOARD_SIZE = (500, 750)
    
    @classmethod
    def validate(cls):
        """Validates system integrity and prepares workspace."""
        logger.info("[SYSTEM] Initializing Arvyn Integrity Check...")
        
        if not cls.GEMINI_API_KEY:
            logger.critical("[CRITICAL] GEMINI_API_KEY is missing. Check your .env file.")
            return False
            
        try:
            os.makedirs(cls.SCREENSHOT_PATH, exist_ok=True)
            os.makedirs(os.path.dirname(cls.USER_PROFILE_PATH), exist_ok=True)
            
            logger.info(f"[SUCCESS] Environment Verified. Mode: {cls.GEMINI_MODEL_NAME}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Directory Creation Failure: {e}")
            return False

# --- CRITICAL: EXPORT ALL CONSTANTS FOR DIRECT IMPORT ---
ORB_SIZE = Config.ORB_SIZE
DASHBOARD_SIZE = Config.DASHBOARD_SIZE
ACCENT_COLOR = Config.ACCENT_COLOR
ERROR_COLOR = Config.ERROR_COLOR
SUCCESS_COLOR = Config.SUCCESS_COLOR
GEMINI_API_KEY = Config.GEMINI_API_KEY
GEMINI_MODEL_NAME = Config.GEMINI_MODEL_NAME
SCREENSHOT_PATH = Config.SCREENSHOT_PATH
USER_PROFILE_PATH = Config.USER_PROFILE_PATH
DEFAULT_VOICE_ID = Config.DEFAULT_VOICE_ID
COMMAND_TIMEOUT = Config.COMMAND_TIMEOUT
VIEWPORT_WIDTH = Config.VIEWPORT_WIDTH
VIEWPORT_HEIGHT = Config.VIEWPORT_HEIGHT

# Automatic validation on module import
Config.validate()