# 🔬 AI Research Agent v2

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway-blueviolet?style=for-the-badge)](https://your-app.up.railway.app)
[![API Docs](https://img.shields.io/badge/API%20Docs-FastAPI-009688?style=for-the-badge)](https://your-app.up.railway.app/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

A fully autonomous research agent that decomposes topics, searches the web in
parallel, scores sources, extracts findings, and synthesises a cited report —
with **persistent vector memory**, **quality evaluation metrics**, and **PDF export**.

> **Free stack:** Groq (LLaMA 3.3-70B) + Tavily Search + ChromaDB + sentence-transformers

---

## What's new in v2

| Upgrade | What it does | Why it matters |
|---|---|---|
| **1. ChromaDB memory** | Embeds every finding; semantic search across past runs | Demonstrates RAG, not just API chaining |
| **2. LangGraph** | StateGraph with typed state + conditional loop edge | "Agent system" vs "automation script" on resume |
| **3. Async parallel** | `asyncio.gather()` searches all sub-questions at once | 3–6× faster; benchmark-ready talking point |
| **4. Evaluation** | Credibility, citation density, hallucination risk, confidence score | Only research agent with built-in quality metrics |
| **5. Deployment** | Railway (backend) + Vercel (frontend) | Live URL = verifiable project |
| **6. PDF export** | `weasyprint` renders cited PDFs | Ships before Synapse AI ships it |

---

## Architecture

```
INPUT: topic
   │
   ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph StateGraph                        │
│                                                         │
│  Planner ──► Searcher ──► Scorer ──► Summarizer         │
│                ▲               │                        │
│                │    ┌──────────▼──────────┐             │
│                │    │    GapChecker        │             │
│                │    │  gaps found &        │             │
│                └────┤  under loop limit?   │             │
│           loop back │                      │             │
│                     └──────────┬───────────┘             │
│                                │ no gaps / limit hit     │
│                                ▼                        │
│                          Synthesizer                    │
│                                │                        │
│                            Output                       │
└─────────────────────────────────────────────────────────┘
   │
   ├── Markdown report  (output/)
   ├── HTML report       (output/)
   ├── PDF report        (output/)  ← new
   ├── Findings JSON     (output/)
   └── Evaluation JSON   (output/)  ← new

ChromaDB (persistent, ./chroma_db/)
  ← every finding embedded here after summarization
  ← queryable via /memory/search for RAG across past runs
```

---

## Quick start

### 1. Clone & install

```bash
git clone https://github.com/Yuvrajpawar45/AI-Research-Agent-
cd AI-Research-Agent-
pip install -r requirements.txt
```

> **weasyprint system deps (Ubuntu/Debian):**
> ```bash
> sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b
> ```

### 2. Configure keys

```bash
cp .env.example .env
# Paste your GROQ_API_KEY and TAVILY_API_KEY
```

### 3. Run

```bash
# CLI (with optional PDF export)
python main.py "The future of nuclear energy" --pdf

# API server
uvicorn api.main:app --reload
# → http://localhost:8000/docs
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/research` | Run full research pipeline |
| `POST` | `/memory/search` | Semantic search past findings (RAG) |
| `GET`  | `/memory/topics` | List all researched topics |
| `GET`  | `/memory/count` | Total stored findings in ChromaDB |
| `POST` | `/export/pdf` | Download report as PDF |
| `GET`  | `/health` | Health check + feature flags |

### Example: research
```bash
curl -X POST https://your-app.up.railway.app/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "Impact of AI on drug discovery"}'
```

### Example: semantic memory search
```bash
curl -X POST https://your-app.up.railway.app/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning cancer detection", "n": 5}'
```

---

## Evaluation metrics

Every report includes an automated quality evaluation:

| Metric | Description |
|--------|-------------|
| `confidence_score` | Composite 0–1 score (credibility + citations + risk) |
| `source_credibility_score` | Average Tavily source quality score |
| `citation_density` | Citations per 500 words (higher = better supported) |
| `hallucination_risk` | `low` / `medium` / `high` — claims without cited sources |
| `per_section_confidence` | Per-section breakdown for the UI |

---

## Performance benchmark

Parallel vs sequential search (6 sub-questions, ~1s per search):

| Mode | Time |
|------|------|
| Sequential (v1) | ~6.0s |
| Parallel (v2) | ~1.2s |
| **Speedup** | **~5×** |

---

## Deployment

### Backend → Railway (free)

1. Push to GitHub
2. New project at [railway.app](https://railway.app) → Deploy from GitHub
3. Set env vars: `GROQ_API_KEY`, `TAVILY_API_KEY`
4. Railway auto-detects `railway.json`

### Frontend → Vercel (free)

1. Update `NEXT_PUBLIC_API_URL` in `vercel.json` with your Railway URL
2. Import repo at [vercel.com](https://vercel.com)

---

## Configuration (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `MAX_SUB_QUESTIONS` | 6 | Sub-questions to research |
| `SOURCES_PER_QUERY` | 5 | Web results per search |
| `MIN_CREDIBLE_SOURCES` | 2 | Min findings before loop exits |
| `MAX_SEARCH_LOOPS` | 2 | Max re-search iterations |
| `CONFIDENCE_THRESHOLD` | 0.6 | Min source score to keep |
| `CHROMA_PATH` | `./chroma_db` | ChromaDB persistence path |

---

## Project structure

```
ai-research-agent/
├── main.py                    # CLI entry point (--pdf flag)
├── config.py                  # Settings
├── requirements.txt           # Updated with v2 deps
├── railway.json               # Railway deployment config
├── vercel.json                # Vercel frontend config
├── Procfile
├── agent/
│   ├── graph.py               # ★ LangGraph StateGraph (NEW)
│   ├── memory.py              # ★ ChromaDB vector memory (NEW)
│   ├── evaluation.py          # ★ Quality metrics engine (NEW)
│   ├── export.py              # ★ PDF export via weasyprint (NEW)
│   ├── planner.py             # Step 1: decompose topic
│   ├── scorer.py              # Step 3: score & filter
│   ├── summarizer.py          # Step 4: extract findings
│   ├── gap_checker.py         # Step 5: agentic loop logic
│   ├── synthesizer.py         # Step 6: write report
│   ├── output_writer.py       # Step 7: save files
│   └── llm_client.py          # Groq wrapper
├── api/
│   └── main.py                # ★ FastAPI with all new endpoints (NEW)
├── tools/
│   ├── web_search.py          # ★ Updated with search_async() (UPDATED)
│   └── pdf_parser.py          # PDF input parsing
└── output/                    # Reports saved here
```

---

## Tech stack

| Component | Technology | Cost |
|---|---|---|
| LLM | Groq LLaMA 3.3-70B | Free |
| Search | Tavily API | Free (1000/mo) |
| Orchestration | LangGraph StateGraph | Open source |
| Vector DB | ChromaDB (local) | Free |
| Embeddings | sentence-transformers | Free |
| PDF export | weasyprint | Open source |
| Backend | FastAPI + Railway | Free tier |
| Frontend | Vercel | Free tier |
