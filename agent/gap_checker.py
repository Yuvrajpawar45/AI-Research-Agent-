"""
STEP 5 — Identify Gaps & Decide to Loop or Proceed
The agentic loop: checks coverage, refines queries, triggers re-search.
"""

from agent.llm_client import LLMClient
import config


SYSTEM_REFINER = """You are a research strategist. A research agent searched for information
about a sub-question but didn't find enough credible sources.

Your job: generate a DIFFERENT, more specific search query that might find better sources.
- Change the angle, terminology, or scope
- Don't just repeat the original query
- Try academic terms, synonyms, or more specific phrasing

Return JSON: {"refined_query": "your new search query here"}
"""


class GapChecker:
    def __init__(self):
        self.llm = LLMClient()

    def has_enough_findings(self, findings: list[dict]) -> bool:
        """Check if we have enough credible findings for a sub-question."""
        return len(findings) >= config.MIN_CREDIBLE_SOURCES

    def refine_query(self, original_query: str, sub_question: str) -> str:
        """Generate a refined search query when initial search underperforms."""
        print(f"   🔄 Refining query for: '{sub_question[:60]}...'")

        result = self.llm.chat_json(
            system=SYSTEM_REFINER,
            user=(
                f"Sub-question: {sub_question}\n"
                f"Original search query that didn't work well: {original_query}"
            ),
        )

        refined = result.get("refined_query", original_query)
        print(f"   → Refined query: '{refined}'")
        return refined
