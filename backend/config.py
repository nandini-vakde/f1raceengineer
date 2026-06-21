import os
from dotenv import load_dotenv

load_dotenv()

# Public OpenF1 API (no MongoDB). For local query API, use port 8001 to avoid
# conflicting with this app's uvicorn on 8000:
#   OPENF1_BASE_URL=http://127.0.0.1:8001/v1
OPENF1_BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1").rstrip("/")

CACHE_DIR = os.getenv("F1_CACHE_DIR", "f1_cache")

PURDUE_API_KEY = os.getenv("PURDUE_API_KEY")
PURDUE_BASE_URL = os.getenv("PURDUE_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-oss:120b")
CHAT_ENDPOINT = "https://genai.rcac.purdue.edu/api/chat/completions"