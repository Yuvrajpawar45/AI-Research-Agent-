# 🔬 AI Research Agent

A fully autonomous research agent that takes a broad topic, breaks it into sub-questions, searches the web, scores sources, extracts findings, and writes a cited report — all without you doing anything after the first prompt.

**Free stack:** Groq (LLaMA 3.3-70B) + Tavily Search — both have free tiers, no credit card required.

---

## Architecture

```
 PLAN          TOOLS            DECIDE              EXECUTE
────────    ─────────────    ─────────────────    ──────────────
Step 1      Steps 2 & 4      Steps 3 & 5          Steps 6 & 7

Decompose   Search web    →  Score sources     →  Synthesize
topic  →    Parse PDFs    →  Filter low-qual   →  Write report
            Summarize     →  Re-search if gap  →  Save output
```

---

## Setup (5 minutes)

### 1. Get your free API keys

| Service | URL | Free tier |
|---------|-----|-----------|
| **Groq** | https://console.groq.com | Free — LLaMA 3.3-70B, very fast |
| **Tavily** | https://app.tavily.com | 1,000 searches/month free |

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure keys

```bash
cp .env.example .env
# Edit .env and paste your keys
```

### 4. Run it

```bash
# Interactive mode
python main.py

# Or pass the topic directly
python main.py "Impact of artificial intelligence on healthcare"
python main.py "Climate change adaptation strategies for coastal cities"
python main.py "The future of nuclear energy"
```

---

## Output

Reports are saved to the `output/` folder:

| File | Description |
|------|-------------|
| `<topic>_<timestamp>.md` | Full Markdown report with citations |
| `<topic>_<timestamp>.html` | Styled HTML version (needs `markdown` package) |
| `<topic>_<timestamp>_findings.json` | Raw JSON findings for further processing |

---

## Configuration (`config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_SUB_QUESTIONS` | 6 | How many sub-questions to research |
| `SOURCES_PER_QUERY` | 5 | Web results fetched per search |
| `MIN_CREDIBLE_SOURCES` | 2 | Minimum findings before loop exits |
| `MAX_SEARCH_LOOPS` | 2 | Maximum re-search iterations per question |
| `CONFIDENCE_THRESHOLD` | 0.6 | Minimum source score (0–1) to keep |

---

## How the agentic loop works (Step 5)

```
Search(query)
    ↓
Score & filter sources
    ↓
Summarize each source
    ↓
findings >= MIN_CREDIBLE_SOURCES?
   YES → proceed to next sub-question
   NO  → refine query with LLM → loop back (up to MAX_SEARCH_LOOPS)
```

The agent never uses the same failing query twice — it asks the LLM to try a different angle, different terminology, or narrower scope.

---

## Using local PDFs (optional)

Drop PDF files into a folder and use the parser:

```python
from tools.pdf_parser import parse_pdfs_in_folder
sources = parse_pdfs_in_folder("./papers/")
```

Requires `pymupdf` (already in requirements.txt).

---

## Project structure

```
ai-research-agent/
├── main.py                  # Entry point
├── config.py                # Settings
├── requirements.txt
├── .env.example             # Copy to .env and fill in keys
├── agent/
│   ├── orchestrator.py      # Ties all steps together
│   ├── planner.py           # Step 1: decompose topic
│   ├── scorer.py            # Step 3: score & filter sources
│   ├── summarizer.py        # Step 4: extract findings
│   ├── gap_checker.py       # Step 5: agentic loop logic
│   ├── synthesizer.py       # Step 6: write the report
│   ├── output_writer.py     # Step 7: save files
│   └── llm_client.py        # Groq API wrapper
├── tools/
│   ├── web_search.py        # Tavily search tool
│   └── pdf_parser.py        # PDF parsing tool
└── output/                  # Reports appear here
```

---

## Why these free APIs?

- **Groq** — Fastest free LLM API available. LLaMA 3.3-70B matches GPT-4 quality on many tasks. No credit card, generous rate limits.
- **Tavily** — Purpose-built for AI agents. Returns clean, chunked content (not raw HTML). Free tier handles ~33 full research runs/month.

---

## Troubleshooting

**`GROQ_API_KEY not set`** → Make sure `.env` exists and has your key (copy from `.env.example`)

**`TAVILY_API_KEY not set`** → Same as above for Tavily key

**Rate limit errors** → Groq free tier has per-minute limits. The agent will raise an error; just wait 60 seconds and retry.

**Empty report sections** → Tavily free tier exhausted (1000/month). Check your usage at app.tavily.com
