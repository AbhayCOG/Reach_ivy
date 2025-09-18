# Gemini LLM API service
import os
import httpx
from dotenv import load_dotenv

class LLMService:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.url = os.getenv("GEMINI_ENDPOINT")
        self.headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key
        }

    async def call_gemini_api(self, prompt: str) -> str:
        data = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }
        timeout = httpx.Timeout(60)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(self.url, headers=self.headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']["parts"][0]["text"]
