"""
STEP 1 — Plan
Decomposes the user's broad topic into specific, answerable sub-questions
and decides the output format / structure.
"""

from agent.llm_client import LLMClient
import config


SYSTEM_PLANNER = """You are a research planning assistant.
Your job is to decompose a broad research topic into specific, focused sub-questions
that together cover the topic comprehensively.

Return a JSON object with this exact structure:
{
  "title": "Full research title",
  "sub_questions": [
    "Sub-question 1?",
    "Sub-question 2?",
    ...
  ],
  "report_sections": [
    "Section title 1",
    "Section title 2",
    ...
  ],
  "sources_needed_per_question": 3
}
"""


class Planner:
    def __init__(self):
        self.llm = LLMClient()

    def decompose(self, topic: str, max_sub_questions: int | None = None) -> dict:
        """Break the topic into sub-questions and plan the report structure."""
        print(f"\n📋 [PLAN] Decomposing topic: '{topic}'")

        question_count = max_sub_questions or config.MAX_SUB_QUESTIONS

        result = self.llm.chat_json(
            system=SYSTEM_PLANNER,
            user=(
                f"Research topic: {topic}\n\n"
                f"Generate {question_count} specific sub-questions "
                f"and a matching report outline."
            ),
        )

        print(f"   → {len(result['sub_questions'])} sub-questions generated")
        for i, q in enumerate(result["sub_questions"], 1):
            print(f"   {i}. {q}")

        return result
