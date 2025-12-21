import os
import logging
import sys
import torch
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --- 1. HIGH-DPI & UI STABILITY ---
# Forces the OS to handle scaling correctly to prevent coordinate mismatches
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

# --- 2. ROBUST LOGGING & ENCODING HARDENING ---
class SafeStreamHandler(logging.StreamHandler):
    """
    Advanced stream handler with character-fallback logic.
    Prevents 'charmap' errors in Windows terminals when logging VLM analysis.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # Fallback for legacy CMD/PowerShell encodings
            msg = self.format(record)
            safe_msg = msg.encode('ascii', 'replace').decode('ascii')
            self.stream.write(safe_msg + self.terminator)
            self.flush()

# Suppress noisy third-party logs to focus on Agent Reasoning speed
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.ERROR)

log_format = '%(asctime)s | %(levelname)s | [%(name)s] | %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter(log_format, datefmt=date_format)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# File Handler for long-term session auditing
file_handler = logging.FileHandler("arvyn_session.log", encoding='utf-8')
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

# Safe Terminal Handler
stream_handler = SafeStreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
root_logger.addHandler(stream_handler)

logger = logging.getLogger("ArvynConfig")

class Config:
    """
    Central configuration for Agent Arvyn v4.1.
    OPTIMIZED: Speed-boosted for entry-level RTX GPUs (RTX 2050/3050).
    FIXED: Added missing MAX_NEW_TOKENS constants to resolve ImportError.
    """
    
    # --- AI MODEL SETTINGS (QWEN2.5-VL 3B) ---
    QWEN_MODEL_NAME = os.getenv("QWEN_MODEL_NAME", "Qwen/Qwen2.5-VL-3B-Instruct")
    DEVICE = os.getenv("AI_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    
    # SPEED UP: fp16 is faster on mobile/entry RTX GPUs than bf16
    TORCH_DTYPE = "fp16" 
    
    # QUANTIZATION: 4-bit loading drastically improves speed on 4GB VRAM
    USE_4BIT_QUANTIZATION = True 
    
    # TOKEN LIMITS: Faster generation by capping unnecessary output
    MAX_NEW_TOKENS_PARSE = 512
    MAX_NEW_TOKENS_ACTION = 1024
    
    # --- AUTONOMY & INTEGITY ---
    AUTONOMOUS_MODE = True
    STRICT_DATA_INTEGRITY = True 
    MAX_TASK_RECURSION = 60 
    
    # --- KINETIC & BROWSER (1920x1080 Native) ---
    VIEWPORT_WIDTH = 1920
    VIEWPORT_HEIGHT = 1080
    HEADLESS = os.getenv("HEADLESS_MODE", "False").lower() == "true"
    BROWSER_TYPE = "playwright"
    SCREENSHOT_PATH = "screenshots"
    
    # --- SPEED & RELIABILITY TUNING ---
    KINETIC_OFFSET_BASE = 8  
    UI_HYDRATION_BUFFER = 2.5 
    RETRY_ATTEMPTS = 2        
    
    # --- DATA & MEMORY ---
    USER_PROFILE_PATH = "data/user_profile.json"
    LOG_FILE_PATH = "arvyn_session.log"
    
    # --- VOICE & STT ---
    DEFAULT_VOICE_ID = None  
    STT_ENERGY_THRESHOLD = 350 
    STT_PAUSE_THRESHOLD = 1.2
    COMMAND_TIMEOUT = 45 
    
    # --- UI & ORB THEMING ---
    THEME = "GlassMorphism_V3"
    ORB_COLOR = "#00d2ff"
    ACCENT_COLOR = "#00d2ff"
    ERROR_COLOR = "#ff4b2b"
    SUCCESS_COLOR = "#2ecc71"
    
    ORB_SIZE = 70 
    DASHBOARD_SIZE = (350, 620) 
    
    @classmethod
    def validate(cls):
        """Pre-flight check optimized for limited VRAM environments."""
        logger.info("[SYSTEM] Verifying High-Speed Autonomous Environment...")
        
        # 1. Hardware & VRAM Awareness
        if cls.DEVICE == "cuda":
            try:
                import torch
                vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                logger.info(f"[HARDWARE] {torch.cuda.get_device_name(0)} ({vram_gb:.1f}GB VRAM)")
                if cls.USE_4BIT_QUANTIZATION:
                    logger.info("[SPEED] 4-Bit Quantization ENABLED for low-latency inference.")
                if vram_gb < 5:
                    logger.warning("[MEMORY] Ultra-low VRAM detected. Using 4-bit is mandatory for speed.")
            except Exception as e:
                logger.error(f"[ERROR] GPU Check failed: {e}")
                cls.DEVICE = "cpu"
        
        # 2. Workspace Preparation
        try:
            os.makedirs(cls.SCREENSHOT_PATH, exist_ok=True)
            os.makedirs(os.path.dirname(cls.USER_PROFILE_PATH), exist_ok=True)
            
            logger.info(f"[SUCCESS] Environment Verified. Engine: {cls.QWEN_MODEL_NAME} on {cls.DEVICE}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Directory Creation Failure: {e}")
            return False

# --- EXPORT ALL CONSTANTS FOR GLOBAL ACCESSIBILITY ---
ORB_SIZE = Config.ORB_SIZE
DASHBOARD_SIZE = Config.DASHBOARD_SIZE
ACCENT_COLOR = Config.ACCENT_COLOR
ERROR_COLOR = Config.ERROR_COLOR
SUCCESS_COLOR = Config.SUCCESS_COLOR
QWEN_MODEL_NAME = Config.QWEN_MODEL_NAME
DEVICE = Config.DEVICE
TORCH_DTYPE = Config.TORCH_DTYPE
USE_4BIT_QUANTIZATION = Config.USE_4BIT_QUANTIZATION
MAX_NEW_TOKENS_PARSE = Config.MAX_NEW_TOKENS_PARSE
MAX_NEW_TOKENS_ACTION = Config.MAX_NEW_TOKENS_ACTION
SCREENSHOT_PATH = Config.SCREENSHOT_PATH
USER_PROFILE_PATH = Config.USER_PROFILE_PATH
DEFAULT_VOICE_ID = Config.DEFAULT_VOICE_ID
COMMAND_TIMEOUT = Config.COMMAND_TIMEOUT
VIEWPORT_WIDTH = Config.VIEWPORT_WIDTH
VIEWPORT_HEIGHT = Config.VIEWPORT_HEIGHT
AUTONOMOUS_MODE = Config.AUTONOMOUS_MODE
UI_HYDRATION_BUFFER = Config.UI_HYDRATION_BUFFER

# Run initial validation
Config.validate()