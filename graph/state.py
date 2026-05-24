"""
ResearchState — the single shared TypedDict that flows through every node.

LangGraph passes this dict between nodes. Each node reads what it needs
and writes only its own fields. The graph engine merges the updates.

Field ownership:
  topic           → set by caller, read-only for all nodes
  plan            → written by planner_node
  current_q_idx   → written by search_node (advances the sub-question cursor)
  current_query   → written by search_node / gap_node
  raw_sources     → written by search_node, consumed by scorer_node
  scored_sources  → written by scorer_node, consumed by summarizer_node
  loop_count      → written by gap_node (tracks re-search iterations)
  all_findings    → written by summarizer_node (accumulated across all questions)
  q_findings      → written by summarizer_node (findings for current question only)
  report_md       → written by synthesizer_node
  report_path     → written by deliver_node
  status_log      → appended by every node (used by FastAPI SSE stream)
  error           → set on failure, triggers END early
"""

from typing import TypedDict, Annotated
import operator


def _merge_findings(a: dict, b: dict) -> dict:
    """Custom reducer: merges two {question: [findings]} dicts."""
    merged = dict(a)
    for q, finds in b.items():
        if q in merged:
            merged[q] = merged[q] + finds
        else:
            merged[q] = finds
    return merged


class ResearchState(TypedDict):
    # ── Input ────────────────────────────────────────────────────
    topic: str
    max_sub_questions: int

    # ── Plan (Step 1) ────────────────────────────────────────────
    plan: dict                  # {title, sub_questions, report_sections, ...}

    # ── Per-question loop state ───────────────────────────────────
    current_q_idx: int          # Which sub-question we are working on (0-indexed)
    current_query: str          # Active search query (changes on refinement)
    loop_count: int             # How many re-search loops for current question

    # ── Tool outputs ─────────────────────────────────────────────
    raw_sources: list           # From search_node
    scored_sources: list        # From scorer_node

    # ── Findings accumulation ─────────────────────────────────────
    q_findings: list            # Findings for the *current* sub-question
    all_findings: Annotated[dict, _merge_findings]  # {question: [findings]}

    # ── Output ───────────────────────────────────────────────────
    report_md: str
    report_path: str

    # ── Observability ─────────────────────────────────────────────
    # Annotated with operator.add so each node can append without clobbering
    status_log: Annotated[list, operator.add]

    # ── Error handling ────────────────────────────────────────────
    error: str                  # Non-empty string triggers early exit to END
