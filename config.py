"""
Configuration — loads from .env or environment variables
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Free API keys ──────────────────────────────────────────────
# Groq: https://console.groq.com  (free, very fast LLaMA 3)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Tavily: https://app.tavily.com  (free tier: 1000 searches/month)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ── Model settings ─────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"   # Best free model on Groq
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# ── Agent behaviour ────────────────────────────────────────────
MAX_SUB_QUESTIONS = 6          # How many sub-questions to decompose into
SOURCES_PER_QUERY  = 5         # Web results fetched per sub-question
MIN_CREDIBLE_SOURCES = 2       # Minimum before triggering re-search loop
MAX_SEARCH_LOOPS   = 2         # Maximum re-search iterations
CONFIDENCE_THRESHOLD = 0.6     # Relevance score to keep a source (0-1)
MAX_PARALLEL_RESEARCH = int(os.getenv("MAX_PARALLEL_RESEARCH", "3"))

# ── Output ─────────────────────────────────────────────────────
OUTPUT_DIR = "output"
