import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OPENF1_BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1").rstrip("/")
CACHE_DIR = os.getenv("F1_CACHE_DIR", "f1_cache")
PURDUE_API_KEY = os.getenv("PURDUE_API_KEY")
PURDUE_BASE_URL = os.getenv("PURDUE_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-oss:120b")
CHAT_ENDPOINT = "https://genai.rcac.purdue.edu/api/chat/completions"
