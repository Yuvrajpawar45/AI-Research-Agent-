"""
Research quality evaluator.

Creates transparent, non-LLM metrics for each run so the project can show
source quality, citation coverage, and hallucination risk signals.
"""

from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse


def _domain(url: str) -> str:
    host = urlparse(url or "").netloc.lower()
    return host.removeprefix("www.")


class ResearchEvaluator:
    def evaluate(self, all_findings: dict[str, list[dict]]) -> dict:
        findings = [
            finding
            for question_findings in all_findings.values()
            for finding in question_findings
        ]
        source_urls = [finding.get("source_url", "") for finding in findings]
        domains = [_domain(url) for url in source_urls if url]
        scores = [
            float(finding.get("source_score", 0) or 0)
            for finding in findings
        ]
        cited_claims = sum(
            len(finding.get("key_claims", []) or [])
            + len(finding.get("statistics", []) or [])
            for finding in findings
        )

        findings_count = len(findings)
        unique_sources = len(set(source_urls))
        unique_domains = len(set(domains))
        average_source_score = round(sum(scores) / len(scores), 3) if scores else 0
        citation_density = round(cited_claims / findings_count, 2) if findings_count else 0

        risk_flags = []
        if findings_count == 0:
            risk_flags.append("No extracted findings; report may be unsupported.")
        if unique_sources < 3:
            risk_flags.append("Low source count; add more evidence before trusting conclusions.")
        if unique_domains < 2:
            risk_flags.append("Low domain diversity; findings may come from a narrow source base.")
        if average_source_score < 0.65:
            risk_flags.append("Average source score is below the recommended confidence band.")
        if citation_density < 2:
            risk_flags.append("Low citation density; claims may need more explicit evidence.")

        confidence_score = round(
            min(
                100,
                (average_source_score * 45)
                + (min(unique_sources, 8) / 8 * 25)
                + (min(unique_domains, 5) / 5 * 15)
                + (min(citation_density, 4) / 4 * 15),
            ),
            1,
        )

        return {
            "confidence_score": confidence_score,
            "findings_count": findings_count,
            "unique_sources": unique_sources,
            "unique_domains": unique_domains,
            "average_source_score": average_source_score,
            "citation_density": citation_density,
            "top_domains": Counter(domains).most_common(5),
            "risk_flags": risk_flags,
        }
