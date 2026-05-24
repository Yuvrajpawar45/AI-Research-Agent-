"""
FastAPI backend — exposes the LangGraph research agent over HTTP.

Endpoints:
  GET  /api/health          → health check
  POST /api/run             → blocking run, returns full result as JSON
  POST /api/stream          → Server-Sent Events stream, one event per node step

SSE stream format (one JSON per line, prefixed with "data: "):
  data: {"event":"node_start","node":"search","message":"Searching...","step":2}
  data: {"event":"node_done","node":"scorer","message":"8 sources scored","step":3}
  data: {"event":"result","node":"deliver","message":"Done","data":{...}}
  data: {"event":"error","node":"planner","message":"API key missing"}

Run locally:
  uvicorn api.main:app --reload --port 8000

Then open:  http://localhost:8000/api/docs
"""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from graph.graph  import research_graph
from graph.state  import ResearchState


# ── App setup ─────────────────────────────────────────────────────
app = FastAPI(
    title="AI Research Agent",
    description="Autonomous research agent powered by LangGraph + Groq + Tavily",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────
class RunRequest(BaseModel):
    topic: str
    max_sub_questions: int = 6     # overrides config if provided

class RunResponse(BaseModel):
    title:       str
    report_path: str
    report_md:   str
    findings_count: int
    steps_taken: int
    logs:        list[dict]


# ── Helpers ───────────────────────────────────────────────────────
def _build_initial_state(topic: str, max_sub_questions: int = 6) -> ResearchState:
    """Build the empty initial state for a new run."""
    return ResearchState(
        topic          = topic,
        max_sub_questions = max_sub_questions,
        plan           = {},
        current_q_idx  = 0,
        current_query  = "",
        loop_count     = 0,
        raw_sources    = [],
        scored_sources = [],
        q_findings     = [],
        all_findings   = {},
        report_md      = "",
        report_path    = "",
        status_log     = [],
        error          = "",
    )


def _node_display_name(node: str) -> str:
    names = {
        "planner":      "Planning sub-questions",
        "search":       "Searching the web",
        "scorer":       "Scoring & filtering sources",
        "summarizer_q": "Extracting findings",
        "gap_checker":  "Checking coverage gaps",
        "synthesizer":  "Writing the report",
        "deliver":      "Saving output files",
    }
    return names.get(node, node)


# ── Routes ────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "AI Research Agent", "version": "2.0.0"}


@app.post("/api/run", response_model=RunResponse)
async def run_agent(req: RunRequest):
    """
    Blocking endpoint — runs the full graph and returns when done.
    For quick testing; use /api/stream for real-time progress.
    """
    initial_state = _build_initial_state(req.topic, req.max_sub_questions)

    # LangGraph .invoke() runs the graph to completion
    final_state: ResearchState = await asyncio.to_thread(
        research_graph.invoke, initial_state
    )

    if final_state.get("error"):
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=final_state["error"])

    findings_count = sum(
        len(v) for v in final_state.get("all_findings", {}).values()
    )

    return RunResponse(
        title          = final_state["plan"].get("title", req.topic),
        report_path    = final_state.get("report_path", ""),
        report_md      = final_state.get("report_md", ""),
        findings_count = findings_count,
        steps_taken    = len(final_state.get("status_log", [])),
        logs           = final_state.get("status_log", []),
    )


@app.post("/api/stream")
async def stream_agent(req: RunRequest):
    """
    SSE streaming endpoint — emits one event per graph step.
    The frontend connects here and shows live progress.
    """
    initial_state = _build_initial_state(req.topic, req.max_sub_questions)

    async def event_generator() -> AsyncGenerator[str, None]:
        step = 0

        # LangGraph .stream(..., stream_mode="updates") yields {node_name: partial_state}.
        for update in research_graph.stream(
            initial_state,
            stream_mode="updates",   # yield after each node update
        ):
            if not update:
                continue

            node_name, partial_state = next(iter(update.items()))
            step += 1

            # ── Error in state → emit error event and stop ──────
            if partial_state.get("error"):
                payload = json.dumps({
                    "event":   "error",
                    "node":    node_name,
                    "message": partial_state["error"],
                    "step":    step,
                })
                yield f"data: {payload}\n\n"
                return

            # ── Build message from latest log entry ──────────────
            logs    = partial_state.get("status_log", [])
            message = logs[-1]["msg"] if logs else _node_display_name(node_name)

            # ── Emit progress event ──────────────────────────────
            payload = json.dumps({
                "event":   "node_done",
                "node":    node_name,
                "display": _node_display_name(node_name),
                "message": message,
                "step":    step,
            })
            yield f"data: {payload}\n\n"

            # ── On final deliver node, emit full result ──────────
            if node_name == "deliver" and partial_state.get("report_path"):
                result_payload = json.dumps({
                    "event":      "result",
                    "node":       "deliver",
                    "message":    "Research complete",
                    "step":       step,
                    "data": {
                        "report_path": partial_state.get("report_path", ""),
                    },
                })
                yield f"data: {result_payload}\n\n"

        yield "data: {\"event\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",    # disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/api/logs/{run_id}")
async def get_logs(run_id: str):
    """Placeholder for per-run log retrieval (extend with DB later)."""
    return {"run_id": run_id, "message": "Log persistence not yet implemented"}
