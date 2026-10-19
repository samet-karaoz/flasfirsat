import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "").strip()
SITE_URL = os.getenv("SITE_URL", "https://flasfirsat.com.tr").rstrip("/")

# Video Specs (9:16 Vertical for Reels/Shorts/TikTok)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

# Voice settings (edge-tts)
ENABLE_VOICEOVER = os.getenv("ENABLE_VOICEOVER", "false").strip().lower() in ("true", "1", "yes")
VOICE_NAME = "tr-TR-AhmetNeural"
VOICE_RATE = "+0%"   # Hızlandırma/yavaşlatma örn: "+5%", "-5%"
VOICE_PITCH = "-3Hz" # Hafif daha kalın ve tok bir etki

# Subtitle styling
SUBTITLE_FONT_SIZE = 72
SUBTITLE_PRIMARY_COLOR = "&H0000FFFF"   # BGR format: Yellow (Sarı)
SUBTITLE_SECONDARY_COLOR = "&H00FFFFFF" # BGR format: White (Beyaz)
SUBTITLE_BORDER_COLOR = "&H00000000"    # Black (Siyah Kontur)

# Filigran (hesap adını buraya yaz)
WATERMARK_TEXT = "h e s a p _ a d i"

# Folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Cross-platform Curl & Subprocess Helpers (Windows / Linux / GitHub Actions)
import platform
import subprocess

IS_WINDOWS = platform.system() == "Windows"
CURL_BIN = "curl.exe" if IS_WINDOWS else "curl"
SUBPROCESS_CREATIONFLAGS = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0

def get_curl_cmd(extra_args: list = None) -> list:
    cmd = [CURL_BIN, "-4"]
    if IS_WINDOWS:
        cmd.append("--ssl-no-revoke")
    if extra_args:
        cmd.extend(extra_args)
    return cmd

def safe_run_subprocess(cmd, **kwargs):
    """Windows'ta siyah cmd/konsol ekranlarının anlık açılıp kapanmasını engelleyen sessiz subprocess çalıştırıcı."""
    if IS_WINDOWS:
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        if "startupinfo" not in kwargs:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = si
    return subprocess.run(cmd, **kwargs)

def download_file(url: str, output_path: str) -> bool:
    """Doğrudan Python requests ile dosya indirir (sıfır CMD penceresi)."""
    import requests
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200 and len(r.content) > 1000:
            with open(output_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    cmd = get_curl_cmd(["--max-time", "15", "-s", "-L", url, "-o", output_path])
    res = safe_run_subprocess(cmd)
    return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000

