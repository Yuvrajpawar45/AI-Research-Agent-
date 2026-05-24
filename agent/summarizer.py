"""
STEP 4 — Summarize & Extract per Sub-question
For each accepted source, extract key claims, statistics, and quotes.
Results stored in structured JSON with citations.
"""

from agent.llm_client import LLMClient


SYSTEM_SUMMARIZER = """You are a research analyst. Given a source passage and a research sub-question,
extract the most relevant information.

Return a JSON object with this structure:
{
  "relevant": true,
  "key_claims": ["claim 1", "claim 2", ...],
  "statistics": ["stat 1", "stat 2"],
  "key_quote": "most relevant short quote from the text (or empty string)",
  "summary": "2-3 sentence summary of what this source contributes"
}

If the source is not relevant to the sub-question, return {"relevant": false}.
"""


class Summarizer:
    def __init__(self):
        self.llm = LLMClient()

    def extract(self, source: dict, sub_question: str) -> dict | None:
        """Extract structured findings from a single source."""
        content = source.get("content", "")
        if not content or len(content) < 50:
            return None

        # Truncate very long content to stay within context limits
        content_excerpt = content[:3000]

        prompt = (
            f"Sub-question: {sub_question}\n\n"
            f"Source title: {source.get('title', 'Unknown')}\n"
            f"Source URL: {source.get('url', '')}\n\n"
            f"Content:\n{content_excerpt}"
        )

        try:
            result = self.llm.chat_json(SYSTEM_SUMMARIZER, prompt)
        except Exception as e:
            print(f"   ⚠️  Summarizer error for {source.get('url', '')}: {e}")
            return None

        if not result.get("relevant", False):
            return None

        return {
            "source_title":  source.get("title", ""),
            "source_url":    source.get("url", ""),
            "source_score":  source.get("composite_score", 0),
            "key_claims":    result.get("key_claims", []),
            "statistics":    result.get("statistics", []),
            "key_quote":     result.get("key_quote", ""),
            "summary":       result.get("summary", ""),
        }

    def extract_all(self, sources: list[dict], sub_question: str) -> list[dict]:
        """Extract findings from all sources for a sub-question."""
        findings = []
        for src in sources:
            finding = self.extract(src, sub_question)
            if finding:
                findings.append(finding)
        return findings
