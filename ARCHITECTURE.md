# Architecture — AI Research Agent v2

## LangGraph StateGraph

```
START
  │
  ▼
┌─────────────────────────────────────────────┐
│  planner_node                               │
│  • LLM decomposes topic into sub-questions  │
│  • Sets: plan, current_q_idx=0, loop_count  │
└──────────────┬──────────────────────────────┘
               │ (error?) ──────────────────► END
               │
               ▼
┌─────────────────────────────────────────────┐  ◄──────────────────────┐
│  search_node                                │                         │
│  • Tavily web search for current_query      │                         │
│  • Sets: raw_sources                        │                         │
└──────────────┬──────────────────────────────┘                         │
               │                                                         │
               ▼                                                         │
┌─────────────────────────────────────────────┐                         │
│  scorer_node                                │                         │
│  • Score: relevance × credibility × recency │                         │
│  • Drops sources below threshold (0.6)      │                         │
│  • Sets: scored_sources                     │                         │
└──────────────┬──────────────────────────────┘                         │
               │                                                         │
               ▼                                                         │
┌─────────────────────────────────────────────┐                         │
│  summarizer_node                            │                         │
│  • LLM extracts claims, stats, quotes       │                         │
│  • Appends to q_findings                    │                         │
│  • Sets: q_findings (accumulated)           │                         │
└──────────────┬──────────────────────────────┘                         │
               │                                                         │
               ▼                                                         │
┌─────────────────────────────────────────────┐                         │
│  gap_checker_node                           │                         │
│  • len(q_findings) >= MIN_CREDIBLE?         │                         │
│    YES or max_loops → advance to next Q     │                         │
│    NO → refine query, increment loop_count  │                         │
└──────────────┬──────────────────────────────┘                         │
               │                                                         │
        route_after_gap()                                               │
               │                                                         │
    ┌──────────┴────────────┐                                           │
    │                       │                                           │
    │ still questions left  │ all questions done                        │
    │                       │                                           │
    └──── back to search ───┘                                           │
               │                                                        │
               └────────────────────────────────────────────────────────┘
               (loop: same question with refined query,
                OR next question with reset state)

               │ all_questions_done
               ▼
┌─────────────────────────────────────────────┐
│  synthesizer_node                           │
│  • LLM writes full cited report from JSON   │
│  • Sets: report_md                          │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  deliver_node                               │
│  • Saves .md, .html, _findings.json         │
│  • Sets: report_path                        │
└──────────────┬──────────────────────────────┘
               │
               ▼
             END
```

## Shared State (`ResearchState`)

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `topic` | str | caller | planner |
| `plan` | dict | planner | all |
| `current_q_idx` | int | gap_checker | search, gap_checker |
| `current_query` | str | gap_checker | search |
| `loop_count` | int | gap_checker | gap_checker |
| `raw_sources` | list | search | scorer |
| `scored_sources` | list | scorer | summarizer |
| `q_findings` | list | summarizer | gap_checker |
| `all_findings` | dict | gap_checker | synthesizer |
| `report_md` | str | synthesizer | deliver |
| `report_path` | str | deliver | caller |
| `status_log` | list[dict] | every node | FastAPI SSE |
| `error` | str | planner | route_after_planner |

## Conditional Edges

```
route_after_planner(state):
  error?  → END
  else    → search

route_after_gap(state):
  all questions done (idx >= total)  → synthesizer
  else (loop or next question)       → search
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/run` | Blocking — returns full result as JSON |
| POST | `/api/stream` | SSE streaming — one event per node |
| GET | `/api/docs` | Swagger UI |

## SSE Event Format

```json
{"event": "node_done", "node": "scorer", "display": "Scoring & filtering sources", "message": "8 sources passed threshold", "step": 3}
{"event": "result", "node": "deliver", "message": "Research complete", "data": {"report_path": "output/..."}}
{"event": "error", "node": "planner", "message": "GROQ_API_KEY not set"}
{"event": "done"}
```

## Tech Stack

| Layer | Technology | Free |
|-------|-----------|------|
| Agent framework | LangGraph 0.2.28 | ✅ |
| LLM | Groq LLaMA 3.3-70B | ✅ |
| Web search | Tavily API | ✅ 1000/month |
| Backend | FastAPI + uvicorn | ✅ |
| Streaming | Server-Sent Events | ✅ |
| Deploy backend | Railway | ✅ |
| Deploy frontend | Vercel | ✅ |
