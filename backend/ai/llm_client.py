import requests

from config import (
    PURDUE_API_KEY,
    CHAT_ENDPOINT,
    MODEL_NAME,
)

def generate(prompt: str) -> str:

    headers = {
        "Authorization": f"Bearer {PURDUE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.5,
    }

    response = requests.post(
        CHAT_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]