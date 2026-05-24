"""
Graph Nodes — one function per node.

Contract: every node receives ResearchState, returns a partial dict
of only the fields it modified. LangGraph merges it into the shared state.

Node order in the graph:
  planner → search → scorer → summarizer → gap_checker
                                               ↓           ↓
                                          (loop back)  (advance/done)
                                               ↑
                                            search
  ... after all questions answered ...
  synthesizer → deliver → END
"""

from __future__ import annotations
import asyncio
from datetime import datetime

from agent.llm_client    import LLMClient
from agent.planner       import Planner
from agent.scorer        import SourceScorer
from agent.summarizer    import Summarizer
from agent.gap_checker   import GapChecker
from agent.synthesizer   import Synthesizer
from agent.output_writer import save_report
from tools.web_search    import WebSearchTool
from graph.state         import ResearchState
import config


# ── Singletons (one LLM client shared across nodes) ──────────────
_planner     = Planner()
_searcher    = WebSearchTool()
_scorer      = SourceScorer()
_summarizer  = Summarizer()
_gap_checker = GapChecker()
_synthesizer = Synthesizer()


def _log(msg: str) -> list:
    """Helper: build a log entry list for status_log."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")
    return [{"ts": ts, "msg": msg}]


# ─────────────────────────────────────────────────────────────────
# NODE 1 — Planner
# ─────────────────────────────────────────────────────────────────
def planner_node(state: ResearchState) -> dict:
    """
    Decomposes the topic into sub-questions and a report outline.
    Sets: plan, current_q_idx, current_query, loop_count, q_findings
    """
    topic = state["topic"]
    max_sub_questions = state.get("max_sub_questions") or config.MAX_SUB_QUESTIONS
    logs  = _log(f"[PLAN] Decomposing: '{topic}'")

    try:
        plan = _planner.decompose(topic, max_sub_questions=max_sub_questions)
    except Exception as e:
        return {"error": f"Planner failed: {e}", "status_log": logs}

    first_q = plan["sub_questions"][0] if plan["sub_questions"] else ""
    logs += _log(f"[PLAN] {len(plan['sub_questions'])} sub-questions generated")

    return {
        "plan":          plan,
        "current_q_idx": 0,
        "current_query": first_q,
        "loop_count":    0,
        "q_findings":    [],
        "all_findings":  {},
        "status_log":    logs,
        "error":         "",
    }


# ─────────────────────────────────────────────────────────────────
# NODE 2 — Searcher
# ─────────────────────────────────────────────────────────────────
def search_node(state: ResearchState) -> dict:
    """
    Runs the web search for the current_query.
    Sets: raw_sources
    """
    query    = state["current_query"]
    q_idx    = state["current_q_idx"]
    total    = len(state["plan"]["sub_questions"])
    loop_num = state["loop_count"]

    tag  = "SEARCH" if loop_num == 0 else f"RE-SEARCH #{loop_num}"
    logs = _log(f"[{tag}] Q{q_idx+1}/{total}: '{query[:65]}'")

    try:
        raw_sources = _searcher.search(query)
        logs += _log(f"[SEARCH] {len(raw_sources)} results returned")
    except Exception as e:
        logs += _log(f"[SEARCH] ⚠ Failed: {e}")
        raw_sources = []

    return {"raw_sources": raw_sources, "status_log": logs}


# ─────────────────────────────────────────────────────────────────
# NODE 3 — Scorer
# ─────────────────────────────────────────────────────────────────
def scorer_node(state: ResearchState) -> dict:
    """
    Scores and filters raw_sources by relevance, credibility, recency.
    Sets: scored_sources
    """
    sub_question = state["plan"]["sub_questions"][state["current_q_idx"]]
    raw          = state.get("raw_sources", [])
    logs         = _log(f"[SCORE] Scoring {len(raw)} sources...")

    scored = _scorer.score_and_filter(raw, sub_question)
    logs  += _log(f"[SCORE] {len(scored)} sources passed threshold "
                  f"(>={config.CONFIDENCE_THRESHOLD})")

    return {"scored_sources": scored, "status_log": logs}


# ─────────────────────────────────────────────────────────────────
# NODE 4 — Summarizer
# ─────────────────────────────────────────────────────────────────
def summarizer_node(state: ResearchState) -> dict:
    """
    Extracts structured findings from each scored source.
    Appends new findings to q_findings (current question).
    Sets: q_findings, all_findings (partial — only current question updated)
    """
    sub_question  = state["plan"]["sub_questions"][state["current_q_idx"]]
    scored        = state.get("scored_sources", [])
    prev_findings = list(state.get("q_findings", []))

    logs = _log(f"[SUMMARIZE] Extracting from {len(scored)} sources...")

    new_findings = _summarizer.extract_all(scored, sub_question)
    q_findings   = prev_findings + new_findings

    logs += _log(f"[SUMMARIZE] {len(new_findings)} new findings "
                 f"({len(q_findings)} total for this question)")

    return {
        "q_findings":   q_findings,
        "status_log":   logs,
    }


# ─────────────────────────────────────────────────────────────────
# NODE 5 — Gap Checker
# ─────────────────────────────────────────────────────────────────
def gap_checker_node(state: ResearchState) -> dict:
    """
    Decides whether to loop back (refine + re-search) or advance.

    This node only updates routing-relevant state:
      - loop_count  (incremented if looping)
      - current_query (refined query if looping)
      - all_findings / q_findings (flushed when advancing)
      - current_q_idx (incremented when advancing)

    The actual routing decision is made by the conditional edge
    function `route_after_gap` below — it reads state AFTER this node runs.
    """
    q_idx        = state["current_q_idx"]
    sub_question = state["plan"]["sub_questions"][q_idx]
    q_findings   = state.get("q_findings", [])
    loop_count   = state.get("loop_count", 0)
    total        = len(state["plan"]["sub_questions"])
    logs         = []

    has_enough = _gap_checker.has_enough_findings(q_findings)

    if has_enough or loop_count >= config.MAX_SEARCH_LOOPS:
        # ── Advance to next question ────────────────────────────
        status = "satisfied" if has_enough else f"max loops ({loop_count}) reached"
        logs  += _log(f"[GAP] Q{q_idx+1}: {status} — {len(q_findings)} findings")

        next_idx  = q_idx + 1
        next_q    = (state["plan"]["sub_questions"][next_idx]
                     if next_idx < total else "")

        return {
            "all_findings":  {sub_question: q_findings},   # reducer merges this
            "q_findings":    [],                             # reset for next Q
            "current_q_idx": next_idx,
            "current_query": next_q,
            "loop_count":    0,                              # reset loop counter
            "status_log":    logs,
        }
    else:
        # ── Loop back: refine query and re-search ───────────────
        logs       += _log(f"[GAP] Q{q_idx+1}: only {len(q_findings)} findings "
                           f"— refining query (loop {loop_count+1})")
        refined_q   = _gap_checker.refine_query(state["current_query"], sub_question)
        logs       += _log(f"[GAP] Refined query: '{refined_q[:65]}'")

        return {
            "current_query": refined_q,
            "loop_count":    loop_count + 1,
            "status_log":    logs,
        }


# ─────────────────────────────────────────────────────────────────
# NODE 6 — Synthesizer
# ─────────────────────────────────────────────────────────────────
def synthesizer_node(state: ResearchState) -> dict:
    """
    Feeds all structured findings into the final LLM synthesis prompt.
    Sets: report_md
    """
    plan         = state["plan"]
    all_findings = state.get("all_findings", {})
    total_finds  = sum(len(v) for v in all_findings.values())

    logs  = _log(f"[SYNTHESIZE] Writing report from {total_finds} total findings...")
    report_md = _synthesizer.write_report(plan, all_findings)
    logs += _log(f"[SYNTHESIZE] Report written ({len(report_md):,} chars)")

    return {"report_md": report_md, "status_log": logs}


# ─────────────────────────────────────────────────────────────────
# NODE 7 — Deliver
# ─────────────────────────────────────────────────────────────────
def deliver_node(state: ResearchState) -> dict:
    """
    Saves report to disk (Markdown + HTML + JSON findings).
    Sets: report_path
    """
    logs = _log("[DELIVER] Saving report files...")

    report_path = save_report(
        title        = state["plan"]["title"],
        report_md    = state["report_md"],
        all_findings = state["all_findings"],
    )
    logs += _log(f"[DELIVER] Saved → {report_path}")

    return {"report_path": report_path, "status_log": logs}


# ─────────────────────────────────────────────────────────────────
# CONDITIONAL EDGE FUNCTIONS — used by graph.add_conditional_edges()
# ─────────────────────────────────────────────────────────────────

def route_after_gap(state: ResearchState) -> str:
    """
    Called after gap_checker_node. Returns the name of the next node.

    Possible routes:
      "search"      — loop back, refine query and re-search
      "synthesizer" — all questions done, move to synthesis
      "search_next" — advance to next question (maps to "search" node)
    """
    q_idx = state["current_q_idx"]
    total = len(state["plan"]["sub_questions"])

    if q_idx >= total:
        # All questions answered — synthesize
        return "synthesizer"

    loop_count = state.get("loop_count", 0)
    if loop_count > 0:
        # loop_count was incremented — we are looping back
        return "search"

    # loop_count was reset to 0 — we advanced to next question
    return "search"


def route_after_planner(state: ResearchState) -> str:
    """Guard: if planner failed, go to END immediately."""
    if state.get("error"):
        return "end"
    return "search"
