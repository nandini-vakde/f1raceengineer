import os

# Public OpenF1 API (no MongoDB). For local query API, use port 8001 to avoid
# conflicting with this app's uvicorn on 8000:
#   OPENF1_BASE_URL=http://127.0.0.1:8001/v1
OPENF1_BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1").rstrip("/")

CACHE_DIR = os.getenv("F1_CACHE_DIR", "f1_cache")
