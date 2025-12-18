import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environmental variables
load_dotenv()

# ==========================================
# 1. DIRECTORY & LOGGING MANAGEMENT
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Centralized Logging for Advanced Debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / "arvyn_debug.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("ArvynCore")

# Path to the user profile JSON
USER_PROFILE_PATH = DATA_DIR / "user_profile.json"

# ==========================================
# 2. API CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not GEMINI_API_KEY:
    logger.error("CRITICAL: GEMINI_API_KEY is missing from .env!")

# ==========================================
# 3. UI & GLASS MORPHISM CONSTANTS
# ==========================================
WINDOW_TITLE = "Agent Arvyn"
ORB_SIZE = (100, 100)
DASHBOARD_SIZE = (600, 750) 

ACCENT_COLOR = "#0078D4"
TEXT_COLOR = "#FFFFFF"

GLASS_STYLE = """
    QMainWindow {
        background-color: rgba(20, 20, 20, 220);
        border: 1px solid rgba(255, 255, 255, 20);
        border-radius: 15px;
    }
    QWidget#Orb {
        background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                          stop:0 rgba(0, 120, 212, 255), stop:1 rgba(0, 200, 255, 255));
        border-radius: 50px;
    }
    QLabel { color: white; font-family: 'Segoe UI'; font-size: 11pt; }
    QTextEdit {
        background-color: rgba(10, 10, 10, 150);
        color: #00FFCC;
        border: 1px solid rgba(255, 255, 255, 30);
        border-radius: 8px;
        font-family: 'Consolas', monospace;
    }
    QPushButton {
        background-color: rgba(255, 255, 255, 15);
        color: white;
        border: 1px solid rgba(255, 255, 255, 40);
        padding: 10px;
        border-radius: 6px;
    }
    QPushButton:hover { background-color: rgba(0, 120, 212, 180); }
"""

# ==========================================
# 4. AUTOMATION & VOICE
# ==========================================
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "False").lower() == "true"
BROWSER_TIMEOUT = 60000 
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
VOICE_RATE = 180
VOICE_VOLUME = 1.0
VOICE_GENDER_INDEX = 1 
VISION_CONFIDENCE_THRESHOLD = 0.8