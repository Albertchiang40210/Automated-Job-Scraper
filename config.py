import os
from dotenv import load_dotenv

load_dotenv()


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


KEYWORDS = [k.strip() for k in os.getenv("JOB_KEYWORDS", "AI Engineer,Python,軟體工程師").split(",") if k.strip()]
LIMIT_PER_SOURCE = _int("JOB_LIMIT", 10)
SCORE_THRESHOLD = _int("SCORE_THRESHOLD", 75)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# Gemini 免費版約 3 次/分鐘 -> 最小呼叫間隔(秒)
GEMINI_MIN_INTERVAL = _int("GEMINI_MIN_INTERVAL", 21)
SEEN_FILE = os.getenv("SEEN_FILE", "seen_jobs.json")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
