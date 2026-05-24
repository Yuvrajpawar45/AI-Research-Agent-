"""
LLM client — wraps Groq's OpenAI-compatible API.
Groq is free, supports LLaMA 3.3-70B, and is extremely fast.
"""

import json
from openai import OpenAI
import config


class LLMClient:
    def __init__(self):
        if not config.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY not set.\n"
                "Get a free key at https://console.groq.com and add it to .env"
            )
        self.client = OpenAI(
            api_key=config.GROQ_API_KEY,
            base_url=config.GROQ_BASE_URL,
        )
        self.model = config.GROQ_MODEL

    def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """Single-turn chat completion."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return response.choices[0].message.content.strip()

    def chat_json(self, system: str, user: str) -> dict | list:
        """Chat completion that returns parsed JSON."""
        system_json = system + "\n\nYou MUST respond with valid JSON only — no markdown, no commentary."
        raw = self.chat(system_json, user, temperature=0.1)
        # Strip markdown fences if model adds them anyway
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw)
