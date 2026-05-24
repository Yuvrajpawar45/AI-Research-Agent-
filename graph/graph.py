"""
Research Graph — compiles the LangGraph StateGraph.

Graph topology:

  START
    │
    ▼
 planner ──(error?)──► END
    │
    ▼
 search
    │
    ▼
 scorer
    │
    ▼
 summarizer
    │
    ▼
 gap_checker ──(all questions done)──► synthesizer ──► deliver ──► END
    │
    └──(loop / next question)──► search  (back to top of per-question loop)

The single conditional edge on gap_checker handles:
  - looping back for the same question (query refinement)
  - advancing to the next question
  - exiting to synthesizer when all questions are answered
"""

from langgraph.graph import StateGraph, END

from graph.state import ResearchState
from graph.nodes import (
    planner_node,
    search_node,
    scorer_node,
    summarizer_node,
    gap_checker_node,
    synthesizer_node,
    deliver_node,
    route_after_gap,
    route_after_planner,
)


def build_research_graph() -> StateGraph:
    """
    Constructs and compiles the research agent StateGraph.
    Returns a compiled graph ready for .invoke() or .stream().
    """

    # ── 1. Create graph with our shared state schema ───────────────
    graph = StateGraph(ResearchState)

    # ── 2. Register nodes ──────────────────────────────────────────
    graph.add_node("planner",     planner_node)
    graph.add_node("search",      search_node)
    graph.add_node("scorer",      scorer_node)
    graph.add_node("summarizer_q", summarizer_node)   # per-question summarizer
    graph.add_node("gap_checker", gap_checker_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("deliver",     deliver_node)

    # ── 3. Entry point ─────────────────────────────────────────────
    graph.set_entry_point("planner")

    # ── 4. Fixed edges ─────────────────────────────────────────────
    graph.add_edge("search",       "scorer")
    graph.add_edge("scorer",       "summarizer_q")
    graph.add_edge("summarizer_q", "gap_checker")
    graph.add_edge("synthesizer",  "deliver")
    graph.add_edge("deliver",      END)

    # ── 5. Conditional edge after planner (error guard) ────────────
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "search": "search",
            "end":    END,
        },
    )

    # ── 6. Conditional edge after gap_checker (the agentic loop) ───
    #
    # route_after_gap returns:
    #   "search"      → back to search node (loop or next question)
    #   "synthesizer" → all questions answered, proceed to synthesis
    #
    graph.add_conditional_edges(
        "gap_checker",
        route_after_gap,
        {
            "search":      "search",
            "synthesizer": "synthesizer",
        },
    )

    # ── 7. Compile ─────────────────────────────────────────────────
    return graph.compile()


# ── Module-level singleton — import this in your app ──────────────
research_graph = build_research_graph()
