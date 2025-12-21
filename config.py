import os
import logging
import sys
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --- HIGH-DPI & UI STABILITY ---
# Forces the OS to handle scaling correctly so buttons don't get cut off
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

# --- ROBUST LOGGING CONFIGURATION ---
class SafeStreamHandler(logging.StreamHandler):
    """A stream handler that falls back to stripping non-ASCII characters if encoding fails."""
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            msg = self.format(record)
            self.stream.write(msg.encode('ascii', 'replace').decode('ascii') + self.terminator)
            self.flush()

log_format = '%(asctime)s | %(levelname)s | [%(name)s] | %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter(log_format, datefmt=date_format)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("arvyn_session.log", encoding='utf-8')
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

stream_handler = SafeStreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
root_logger.addHandler(stream_handler)

logger = logging.getLogger("ArvynConfig")

class Config:
    """
    Central configuration for Agent Arvyn.
    UPGRADED: Migrated to Qwen-VL Engine for Vision-Reasoning.
    FEATURES: Full-Autonomy (Zero-Authorization) global flags preserved.
    IMPROVED: Compact UI dimensions for unblocked background interactions.
    """
    
    # --- AI MODEL SETTINGS (MIGRATED TO QWEN) ---
    QWEN_API_KEY = os.getenv("QWEN_API_KEY")
    # Base URL for Qwen (DashScope or OpenAI-compatible provider)
    QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    QWEN_MODEL_NAME = os.getenv("QWEN_MODEL_NAME", "qwen-vl-max-latest")
    
    # --- AUTONOMY & SECURITY SETTINGS ---
    STRICT_AUTONOMY_MODE = True 
    AUTO_APPROVAL = True
    PRIORITIZE_VERIFIED_SITES = True
    
    # --- KINETIC & BROWSER SETTINGS ---
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
    COMMAND_TIMEOUT = 45 
    
    # --- UI SETTINGS ---
    THEME = "GlassMorphism_V2"
    ORB_COLOR = "#00d2ff"
    ACCENT_COLOR = "#00d2ff"
    ERROR_COLOR = "#ff4b2b"
    SUCCESS_COLOR = "#2ecc71"
    ORB_SIZE = 70 
    DASHBOARD_SIZE = (350, 620) 
    
    @classmethod
    def validate(cls):
        """Validates system integrity and prepares workspace."""
        logger.info("[SYSTEM] Initializing Arvyn Integrity Check...")
        
        if not cls.QWEN_API_KEY:
            logger.critical("[CRITICAL] QWEN_API_KEY is missing. Check your .env file.")
            return False
            
        try:
            os.makedirs(cls.SCREENSHOT_PATH, exist_ok=True)
            os.makedirs(os.path.dirname(cls.USER_PROFILE_PATH), exist_ok=True)
            
            autonomy_status = "ENABLED" if cls.STRICT_AUTONOMY_MODE else "DISABLED"
            logger.info(f"[SUCCESS] Environment Verified. Engine: {cls.QWEN_MODEL_NAME}")
            logger.info(f"[SUCCESS] Autonomous Mode: {autonomy_status} (Zero-Auth active).")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Directory Creation Failure: {e}")
            return False

# --- CRITICAL: EXPORT ALL CONSTANTS ---
ORB_SIZE = Config.ORB_SIZE
DASHBOARD_SIZE = Config.DASHBOARD_SIZE
ACCENT_COLOR = Config.ACCENT_COLOR
ERROR_COLOR = Config.ERROR_COLOR
SUCCESS_COLOR = Config.SUCCESS_COLOR
QWEN_API_KEY = Config.QWEN_API_KEY
QWEN_BASE_URL = Config.QWEN_BASE_URL
QWEN_MODEL_NAME = Config.QWEN_MODEL_NAME
SCREENSHOT_PATH = Config.SCREENSHOT_PATH
USER_PROFILE_PATH = Config.USER_PROFILE_PATH
DEFAULT_VOICE_ID = Config.DEFAULT_VOICE_ID
COMMAND_TIMEOUT = Config.COMMAND_TIMEOUT
VIEWPORT_WIDTH = Config.VIEWPORT_WIDTH
VIEWPORT_HEIGHT = Config.VIEWPORT_HEIGHT

# Export Autonomous Flags
STRICT_AUTONOMY_MODE = Config.STRICT_AUTONOMY_MODE
AUTO_APPROVAL = Config.AUTO_APPROVAL

Config.validate()