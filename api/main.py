"""
FastAPI backend — exposes the LangGraph research agent over HTTP,
and serves the static frontend from the same process (one deploy, one URL).

Endpoints:
  GET  /                    -> frontend UI
  GET  /api/health          -> health check
  POST /api/run             -> blocking run, returns full result as JSON
  POST /api/stream          -> Server-Sent Events stream, one event per node step
  GET  /api/report/{name}   -> download a saved report file (md/html/json)

SSE stream format (one JSON per line, prefixed with "data: "):
  data: {"event":"node_done","node":"search","message":"...","step":2}
  data: {"event":"result","node":"deliver","message":"Done","data":{...}}
  data: {"event":"error","node":"planner","message":"API key missing"}
  data: {"event":"done"}

Run locally:
  uvicorn api.main:app --reload --port 8000

Then open:  http://localhost:8000
API docs:   http://localhost:8000/api/docs
"""

import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from graph.graph import research_graph
from graph.state import ResearchState
from agent.evaluator import ResearchEvaluator
import config


# ── Paths ───────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
OUTPUT_DIR = (ROOT / config.OUTPUT_DIR).resolve()


# ── App setup ─────────────────────────────────────────────────────
app = FastAPI(
    title="AI Research Agent",
    description="Autonomous research agent powered by LangGraph + Groq + Tavily",
    version="2.1.0",
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

_evaluator = ResearchEvaluator()


# ── Request / Response models ─────────────────────────────────────
class RunRequest(BaseModel):
    topic: str
    max_sub_questions: int = 6     # overrides config if provided

class RunResponse(BaseModel):
    title:          str
    report_path:    str
    report_md:      str
    findings_count: int
    steps_taken:    int
    logs:           list[dict]
    quality_report: dict


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


def _quality_report(final_state: ResearchState) -> dict:
    """Compute the non-LLM quality/evaluation metrics for a finished run."""
    return _evaluator.evaluate(final_state.get("all_findings", {}))


# ── Frontend ──────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


# ── Routes ────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "AI Research Agent", "version": "2.1.0"}


@app.post("/api/run", response_model=RunResponse)
async def run_agent(req: RunRequest):
    """
    Blocking endpoint — runs the full graph and returns when done.
    For quick testing; use /api/stream for real-time progress in the UI.
    """
    initial_state = _build_initial_state(req.topic, req.max_sub_questions)

    final_state: ResearchState = await asyncio.to_thread(
        research_graph.invoke, initial_state
    )

    if final_state.get("error"):
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
        quality_report = _quality_report(final_state),
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
        last_state: dict = dict(initial_state)

        try:
            for update in research_graph.stream(
                initial_state,
                stream_mode="updates",
            ):
                if not update:
                    continue

                node_name, partial_state = next(iter(update.items()))
                step += 1
                last_state.update(partial_state)

                if partial_state.get("error"):
                    payload = json.dumps({
                        "event":   "error",
                        "node":    node_name,
                        "message": partial_state["error"],
                        "step":    step,
                    })
                    yield f"data: {payload}\n\n"
                    return

                logs = partial_state.get("status_log", [])
                message = logs[-1]["msg"] if logs else _node_display_name(node_name)

                payload = json.dumps({
                    "event":   "node_done",
                    "node":    node_name,
                    "display": _node_display_name(node_name),
                    "message": message,
                    "step":    step,
                })
                yield f"data: {payload}\n\n"

                if node_name == "deliver" and partial_state.get("report_path"):
                    findings_count = sum(
                        len(v) for v in last_state.get("all_findings", {}).values()
                    )
                    result_payload = json.dumps({
                        "event":   "result",
                        "node":    "deliver",
                        "message": "Research complete",
                        "step":    step,
                        "data": {
                            "title":          last_state.get("plan", {}).get("title", req.topic),
                            "report_path":    partial_state.get("report_path", ""),
                            "report_md":      last_state.get("report_md", ""),
                            "findings_count": findings_count,
                            "quality_report": _quality_report(last_state),
                        },
                    })
                    yield f"data: {result_payload}\n\n"
        except Exception as exc:
            # Catches anything a node didn't handle itself — e.g. both Groq
            # models being rate-limited during synthesis. Without this, the
            # exception would kill the SSE stream silently: the frontend log
            # just stops with no error shown, which is exactly the symptom
            # of "run stops right after gap_checker with no synthesize/deliver".
            step += 1
            payload = json.dumps({
                "event":   "error",
                "node":    "pipeline",
                "message": f"Unexpected error: {exc}",
                "step":    step,
            })
            yield f"data: {payload}\n\n"
            return

        yield "data: {\"event\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/api/report/{filename}")
async def get_report(filename: str):
    """Serve a saved report file (md/html/json) for download."""
    name = Path(filename).name  # strip any path components — no traversal
    path = (OUTPUT_DIR / name).resolve()
    if OUTPUT_DIR not in path.parents or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path)


@app.get("/api/logs/{run_id}")
async def get_logs(run_id: str):
    """Placeholder for per-run log retrieval (extend with DB later)."""
    return {"run_id": run_id, "message": "Log persistence not yet implemented"}