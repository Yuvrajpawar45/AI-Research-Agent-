"""
STEP 6 — Synthesize & Write the Report
Feeds all structured findings into a final synthesis prompt.
Writes a coherent, cited report in Markdown.
"""

import json
from agent.llm_client import LLMClient


SYSTEM_SYNTHESIZER = """You are an expert research writer. You have been given structured
research findings for multiple sub-questions on a topic.

Write a comprehensive, well-structured research report in Markdown format.
Requirements:
- Start with an executive summary (2-3 paragraphs)
- One section per sub-question (use the provided section titles)
- Weave in specific claims, statistics, and quotes from the findings
- Add inline citations like [Source Title](URL)
- End with a Conclusions section and a References list
- Write in an authoritative, academic-but-readable tone
- Do NOT make up information — only use what's in the findings
"""


class Synthesizer:
    def __init__(self):
        self.llm = LLMClient()

    def write_report(
        self,
        plan: dict,
        all_findings: dict,  # {sub_question: [finding, ...]}
    ) -> str:
        """Generate the final Markdown report from all findings."""
        print("\n✍️  [EXECUTE] Synthesizing final report...")

        # Build a structured findings summary for the LLM
        findings_text = []
        for i, (question, findings) in enumerate(all_findings.items()):
            section = plan["report_sections"][i] if i < len(plan["report_sections"]) else f"Section {i+1}"
            findings_text.append(f"\n## Sub-question {i+1}: {question}")
            findings_text.append(f"Section title: {section}")
            if not findings:
                findings_text.append("(No findings available for this sub-question)")
                continue
            for f in findings:
                findings_text.append(f"\nSource: {f['source_title']} ({f['source_url']})")
                findings_text.append(f"Summary: {f['summary']}")
                if f["key_claims"]:
                    findings_text.append("Key claims: " + "; ".join(f["key_claims"]))
                if f["statistics"]:
                    findings_text.append("Statistics: " + "; ".join(f["statistics"]))
                if f["key_quote"]:
                    findings_text.append(f'Quote: "{f["key_quote"]}"')

        prompt = (
            f"Research title: {plan['title']}\n\n"
            f"Research findings:\n{''.join(findings_text)}\n\n"
            f"Write the full research report now."
        )

        report_md = self.llm.chat(
            system=SYSTEM_SYNTHESIZER,
            user=prompt,
            temperature=0.4,
        )

        return report_md
