import os

GEMINI_API_KEY     = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY     = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_API_KEY    = os.environ.get("PIXABAY_API_KEY", "")   # optional
YT_CLIENT_ID       = os.environ.get("YT_CLIENT_ID", "")
YT_CLIENT_SECRET   = os.environ.get("YT_CLIENT_SECRET", "")
YT_REFRESH_TOKEN   = os.environ.get("YT_REFRESH_TOKEN", "")

GEMINI_FLASH       = "gemini-2.5-flash"
GEMINI_TTS_MODEL   = "gemini-2.5-flash-preview-tts"
GEMINI_API_BASE    = "https://generativelanguage.googleapis.com/v1beta"

# TTS voices — rotate randomly per video
GEMINI_VOICES      = ["Aoede", "Charon", "Fenrir", "Kore", "Puck"]

# Video specs
SHORTS_W, SHORTS_H = 1080, 1920
LONG_W,   LONG_H   = 1920, 1080
FPS                 = 30

# Publishing cadence (IST = UTC+5:30)
# Short 1: upload 10:00 AM IST → publish 12:00 PM IST noon
# Short 2: upload 05:00 PM IST → publish 07:00 PM IST evening
# Long:    upload 11:30 AM IST → publish 02:00 PM IST weekday

# Minimum gap between Shorts: 4 hours (YouTube algorithm requirement)

TOPIC_LOG_SIZE     = 90   # ~5-6 weeks coverage at 2-3 shorts/day + 1 long/week

# Hook patterns — rotate via random.choice for natural variation
HOOK_PATTERNS = [
    "Did you know {subject}",
    "The reason {thing} works is NOT what you think",
    "{seconds} seconds to understand {topic}",
    "Most people get {topic} completely wrong. Here's why",
    "{event} happened because of one tiny decision",
]

# YouTube category IDs
YT_CATEGORY_EDUCATION  = "27"
YT_CATEGORY_SCIENCE    = "28"

def validate_config():
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not PEXELS_API_KEY:
        missing.append("PEXELS_API_KEY")
    if not YT_CLIENT_ID:
        missing.append("YT_CLIENT_ID")
    if not YT_CLIENT_SECRET:
        missing.append("YT_CLIENT_SECRET")
    if not YT_REFRESH_TOKEN:
        missing.append("YT_REFRESH_TOKEN")
        
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
