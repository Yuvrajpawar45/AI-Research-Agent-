"""
STEP 3 — Score & Filter Sources
Scores each source on relevance, credibility, and recency.
Drops sources below the confidence threshold.
"""

from datetime import datetime
from agent.llm_client import LLMClient
import config


# Domains that get a credibility boost
CREDIBLE_DOMAINS = {
    "high": [
        "nature.com", "science.org", "pubmed.ncbi.nlm.nih.gov", "scholar.google",
        "arxiv.org", "ncbi.nlm.nih.gov", "who.int", "cdc.gov", "gov",
        "edu", "mit.edu", "stanford.edu", "harvard.edu",
    ],
    "medium": [
        "reuters.com", "bbc.com", "nytimes.com", "theguardian.com",
        "wired.com", "techcrunch.com", "forbes.com", "economist.com",
    ],
}


def _domain_score(url: str) -> float:
    url_lower = url.lower()
    for domain in CREDIBLE_DOMAINS["high"]:
        if domain in url_lower:
            return 1.0
    for domain in CREDIBLE_DOMAINS["medium"]:
        if domain in url_lower:
            return 0.75
    return 0.5


def _recency_score(published_date: str) -> float:
    if not published_date:
        return 0.5
    try:
        pub = datetime.fromisoformat(published_date[:10])
        days_old = (datetime.now() - pub).days
        if days_old < 30:   return 1.0
        if days_old < 180:  return 0.85
        if days_old < 365:  return 0.7
        if days_old < 730:  return 0.55
        return 0.4
    except Exception:
        return 0.5


class SourceScorer:
    def __init__(self):
        self.llm = LLMClient()

    def score_and_filter(
        self,
        sources: list[dict],
        sub_question: str,
    ) -> list[dict]:
        """Score sources and return only those above the threshold."""
        if not sources:
            return []

        scored = []
        for src in sources:
            # Tavily already provides a relevance score (0-1)
            tavily_relevance = float(src.get("score", 0.5))
            domain_score     = _domain_score(src.get("url", ""))
            recency_score    = _recency_score(src.get("published_date", ""))

            # Weighted composite score
            composite = (
                tavily_relevance * 0.5 +
                domain_score     * 0.3 +
                recency_score    * 0.2
            )

            src["composite_score"] = round(composite, 3)
            src["domain_score"]    = round(domain_score, 3)
            src["recency_score"]   = round(recency_score, 3)
            scored.append(src)

        # Sort by composite score
        scored.sort(key=lambda x: x["composite_score"], reverse=True)

        # Filter below threshold
        filtered = [
            s for s in scored
            if s["composite_score"] >= config.CONFIDENCE_THRESHOLD
        ]

        print(
            f"   🔍 Scored {len(scored)} sources → "
            f"{len(filtered)} kept (threshold={config.CONFIDENCE_THRESHOLD})"
        )
        return filtered
