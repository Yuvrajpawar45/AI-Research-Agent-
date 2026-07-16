# 🔬 AI Research Agent

**Autonomous research agent built on a 7-node LangGraph state machine** — decomposes a topic into sub-questions, searches the web, scores and filters sources, extracts cited findings, self-corrects on weak evidence, and synthesizes a Markdown report with a built-in, non-LLM confidence/risk evaluation.

[![Live Demo](https://img.shields.io/badge/Live_Demo-view_app-0f766e?style=flat-square)](REPLACE_WITH_YOUR_RAILWAY_URL)
[![API Docs](https://img.shields.io/badge/API_Docs-/api/docs-2563eb?style=flat-square)](REPLACE_WITH_YOUR_RAILWAY_URL/api/docs)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-E8823A?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square)](https://fastapi.tiangolo.com)

---

## Why this exists

Most fresher "research agent" projects are a single LLM call wearing a search-tool costume. This one is built as an actual **state machine with a self-correction loop**: if a sub-question doesn't turn up enough credible evidence, the agent rewrites its own query and re-searches — up to a configurable limit — before giving up and moving on. Every run also produces a transparent, deterministic **quality report** (confidence score, source diversity, citation density, risk flags) instead of just asserting the output is trustworthy.

---

## Architecture

```
User Query
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│                    FastAPI Backend                        │
│   GET  /api/health     POST /api/run     POST /api/stream │
└──────────────────────────┬──────────────────────────────--┘
                            │
                            ▼
┌────────────────────────────────────────────────────────---┐
│              LangGraph StateGraph (graph/graph.py)         │
│                                                             │
│   planner ──► search ──► scorer ──► summarizer_q           │
│                  ▲                        │                │
│                  │                        ▼                │
│                  └──────────────── gap_checker              │
│                     (loop: refine query, re-search   │      │
│                      OR advance to next sub-question) │      │
│                                        │               │      │
│                          (all sub-questions done)      │      │
│                                        ▼                       │
│                              synthesizer ──► deliver            │
└──────────────────────────────────────────────────────────---┘
                            │
                    ┌───────┴────────┐
                    ▼                ▼
              Tavily Search    Groq LLaMA 3.3-70B
```

### State flow

```python
# graph/state.py
class ResearchState(TypedDict):
    topic: str
    plan: dict                                     # after planner
    current_q_idx: int                             # which sub-question is active
    current_query: str                              # refined on gap-check loop
    loop_count: int                                  # re-search attempts, this question
    raw_sources: list                                # after search
    scored_sources: list                             # after scorer
    q_findings: list                                 # findings for current question
    all_findings: Annotated[dict, _merge_findings]   # accumulated across all questions
    report_md: str
    report_path: str
    status_log: Annotated[list, operator.add]        # streamed to the UI via SSE
    error: str
```

---

## Tech stack

| Layer | Technology | Notes |
|---|---|---|
| **Orchestration** | LangGraph 0.2 `StateGraph` | 7 nodes, 2 conditional edges — one is the self-correction loop |
| **LLM** | Groq `llama-3.3-70b-versatile` | OpenAI-compatible API, ~800 tok/s, free tier |
| **Web search** | Tavily Search API | direct HTTP, advanced search depth |
| **Backend** | FastAPI + uvicorn | REST + Server-Sent Events streaming |
| **Evaluation** | Custom non-LLM evaluator (`agent/evaluator.py`) | confidence score, citation density, source/domain diversity, risk flags |
| **Frontend** | Vanilla HTML/CSS/JS | consumes the SSE stream directly via `fetch` + `ReadableStream`, no build step |
| **Deployment** | Railway (or Render) | single process serves both API and frontend |

---

## Features

- **🧠 Query decomposition** — Groq LLM breaks the topic into up to 6 focused sub-questions with a matching report outline
- **🔍 Web search per sub-question** — Tavily, advanced search depth
- **📊 Composite source scoring** — blends Tavily's relevance score, a domain-credibility heuristic (`.edu`/`.gov`/known journals score higher), and a recency decay function
- **🔁 Agentic self-correction** — if a sub-question yields fewer than `MIN_CREDIBLE_SOURCES`, the agent asks the LLM to reformulate the query (different angle/terminology) and re-searches, up to `MAX_SEARCH_LOOPS` times
- **📝 Structured, cited extraction** — each accepted source is parsed into key claims, statistics, and a supporting quote before synthesis, not just dumped into the prompt
- **✅ Built-in quality evaluation** — every run gets a deterministic (non-LLM) confidence score plus explicit risk flags, e.g. *"low domain diversity"* or *"citation density below recommended band"* — a transparency layer most portfolio RAG/agent projects skip entirely
- **🌊 Live streaming UI** — SSE endpoint streams one event per graph node, so the frontend shows real pipeline progress, not a spinner
- **📁 Multi-format export** — every run saves Markdown, HTML, findings JSON, and quality JSON

---

## Project structure

```
AI-Research-Agent-/
├── agent/
│   ├── planner.py       # Node 1: topic → sub-questions + report outline
│   ├── scorer.py        # Node 3: composite relevance/credibility/recency scoring
│   ├── summarizer.py    # Node 4: structured claim/stat/quote extraction per source
│   ├── gap_checker.py   # Node 5: coverage check + query refinement
│   ├── synthesizer.py   # Node 6: final cited Markdown report
│   ├── output_writer.py # Node 7: saves .md / .html / findings.json / quality.json
│   ├── evaluator.py     # Deterministic quality/risk scoring (no LLM call)
│   └── llm_client.py    # Groq client wrapper
├── graph/
│   ├── state.py         # ResearchState TypedDict + custom reducers
│   ├── nodes.py         # node functions + conditional-edge routing logic
│   └── graph.py         # compiles the StateGraph
├── api/
│   └── main.py           # FastAPI app: /api/health, /api/run, /api/stream, serves frontend
├── frontend/
│   └── index.html         # SSE-driven pipeline UI, no build step
├── tools/
│   ├── web_search.py      # Tavily HTTP client
│   └── pdf_parser.py       # optional local PDF ingestion (PyMuPDF)
├── main.py                # CLI entry point (classic orchestrator, parallel sub-questions)
├── Procfile                # web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
└── requirements.txt
```

> Note: `main.py` / `agent/orchestrator.py` is an earlier CLI-only implementation that runs sub-questions **in parallel** via `asyncio.Semaphore`. The deployed LangGraph pipeline (`graph/`) processes sub-questions **sequentially** through the state machine — that trade-off is what makes step-by-step SSE progress possible in the UI.

---

## Quick start (local)

```bash
git clone https://github.com/Yuvrajpawar45/AI-Research-Agent-.git
cd AI-Research-Agent-
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # add GROQ_API_KEY and TAVILY_API_KEY
uvicorn api.main:app --reload --port 8000
```

Open `http://localhost:8000` — the FastAPI app serves the frontend directly.

---

## API reference

### `POST /api/stream` (used by the UI)
Server-Sent Events. One `node_done` event per graph node, a final `result` event with the report + quality metrics, then `done`.

### `POST /api/run`
Blocking — waits for the full run and returns everything as one JSON object (`report_md`, `quality_report`, `logs`, etc).

### `GET /api/health`
```json
{ "status": "ok", "service": "AI Research Agent", "version": "2.1.0" }
```

### `GET /api/report/{filename}`
Downloads a saved report file (`.md`, `.html`, `_findings.json`, `_quality.json`) from the most recent runs.

Full interactive docs at `/api/docs` (Swagger) once running.

---

## Deployment

See [`DEPLOY_TODAY.md`](DEPLOY_TODAY.md) for the exact click-by-click Railway steps. Short version:

1. Push this repo to GitHub (main branch)
2. Railway → New Project → Deploy from GitHub repo
3. Add env vars: `GROQ_API_KEY`, `TAVILY_API_KEY`
4. Railway reads the existing `Procfile` and deploys automatically
5. Replace the badge URLs at the top of this README with your live Railway URL

---

## Roadmap

- [x] LangGraph StateGraph with 7 nodes + self-correction loop
- [x] FastAPI backend with SSE streaming
- [x] Deterministic quality/risk evaluator
- [x] Frontend wired to live SSE stream
- [ ] Deploy to Railway/Render (do this today)
- [ ] Similarity-threshold abstention: refuse to answer a sub-question if best-scoring source is still below a floor, rather than always producing a claim
- [ ] Vector memory (ChromaDB/FAISS) across runs for follow-up questions
- [ ] ArXiv/Semantic Scholar source alongside Tavily for academic queries
- [ ] Tests for scorer, evaluator, and graph routing logic

---

## Resume positioning

> Built an autonomous research agent on a 7-node LangGraph state machine with self-correcting search (query refinement on weak evidence), composite source scoring, and a deterministic post-hoc quality evaluator (confidence score, citation density, risk flags) — deployed with a FastAPI backend streaming live pipeline progress over SSE.

Only use this phrasing once the app is actually live — see `DEPLOY_TODAY.md`.

---

## License

MIT