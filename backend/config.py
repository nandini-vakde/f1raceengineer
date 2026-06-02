from dotenv import load_dotenv
import os

load_dotenv()

PURDUE_API_KEY = os.getenv("PURDUE_API_KEY")
PURDUE_BASE_URL = os.getenv("PURDUE_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-oss:120b")
CHAT_ENDPOINT = "https://genai.rcac.purdue.edu/api/chat/completions"