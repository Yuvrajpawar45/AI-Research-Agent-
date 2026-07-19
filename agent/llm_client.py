"""
LLM client — wraps Groq's OpenAI-compatible API.
Groq is free, supports LLaMA 3.3-70B, and is extremely fast.

Rate-limit handling: Groq's free tier caps llama-3.3-70b-versatile at a
fairly low Tokens-Per-Day (TPD) limit. If that's exhausted, we automatically
fall back to llama-3.1-8b-instant, which has a much higher free-tier TPD,
so a research run keeps working instead of failing with a raw 429.
"""

import json
from openai import OpenAI, RateLimitError
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
        self.fallback_model = config.GROQ_FALLBACK_MODEL

    def _complete(self, model: str, system: str, user: str, temperature: float) -> str:
        response = self.client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return response.choices[0].message.content.strip()

    def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """Single-turn chat completion, with automatic fallback on rate limits."""
        try:
            return self._complete(self.model, system, user, temperature)
        except RateLimitError:
            if not self.fallback_model or self.fallback_model == self.model:
                raise
            return self._complete(self.fallback_model, system, user, temperature)

    def chat_json(self, system: str, user: str) -> dict | list:
        """Chat completion that returns parsed JSON."""
        system_json = system + "\n\nYou MUST respond with valid JSON only — no markdown, no commentary."
        raw = self.chat(system_json, user, temperature=0.1)
        # Strip markdown fences if model adds them anyway
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to salvage JSON if the model added stray text around it.
            # Find whichever opening bracket appears FIRST — that's the real
            # start of the JSON value, regardless of what's nested inside it.
            brace_idx = raw.find("{")
            bracket_idx = raw.find("[")
            candidates = [i for i in (brace_idx, bracket_idx) if i != -1]
            if not candidates:
                raise
            start = min(candidates)
            closer = "}" if raw[start] == "{" else "]"
            end = raw.rfind(closer)
            if end == -1 or end < start:
                raise
            return json.loads(raw[start:end + 1])