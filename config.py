import os
from pathlib import Path
from dotenv import load_dotenv

# Load environmental variables from .env file
load_dotenv()

# ==========================================
# 1. DIRECTORY & PATH MANAGEMENT
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CORE_DIR = BASE_DIR / "core"
GUI_DIR = BASE_DIR / "gui"
TOOLS_DIR = BASE_DIR / "tools"

# Create essential directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Path to the user profile JSON
USER_PROFILE_PATH = DATA_DIR / "user_profile.json"

# ==========================================
# 2. API CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ==========================================
# 3. UI & GLASS MORPHISM CONSTANTS
# ==========================================
WINDOW_TITLE = "Agent Arvyn"
ORB_SIZE = (100, 100)
DASHBOARD_SIZE = (500, 700)

# Branding Colors
ACCENT_COLOR = "#0078D4"  # This was the missing link
TEXT_COLOR = "#FFFFFF"

# Glass Morphism Styling (QSS)
GLASS_STYLE = """
    QMainWindow {
        background-color: rgba(30, 30, 30, 180);
        border: 1px solid rgba(255, 255, 255, 30);
        border-radius: 15px;
    }
    QWidget#Orb {
        background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                          stop:0 rgba(0, 120, 212, 255), stop:1 rgba(0, 200, 255, 255));
        border-radius: 50px;
    }
    QLabel {
        color: white;
        font-family: 'Segoe UI', sans-serif;
    }
    QTextEdit {
        background-color: rgba(0, 0, 0, 100);
        color: #00FFCC;
        border: none;
        font-family: 'Consolas', monospace;
        font-size: 10pt;
    }
    QPushButton {
        background-color: rgba(255, 255, 255, 20);
        color: white;
        border: 1px solid rgba(255, 255, 255, 40);
        padding: 8px;
        border-radius: 5px;
    }
    QPushButton:hover {
        background-color: rgba(0, 120, 212, 150);
    }
"""

# ==========================================
# 4. AUTOMATION & BROWSER SETTINGS
# ==========================================
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "False").lower() == "true"
BROWSER_TIMEOUT = 60000 
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# 5. AUDIO & VOICE SETTINGS
# ==========================================
VOICE_RATE = 180
VOICE_VOLUME = 1.0
VOICE_GENDER_INDEX = 1 

# ==========================================
# 6. STATE MACHINE CONSTANTS
# ==========================================
VISION_CONFIDENCE_THRESHOLD = 0.8