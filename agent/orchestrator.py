"""
Research Orchestrator — ties all 7 steps together into the agentic loop.

Flow:
  Plan → Search → Score → Summarize → GapCheck/Loop → Synthesize → Save
"""

import asyncio
from agent.planner       import Planner
from agent.scorer        import SourceScorer
from agent.summarizer    import Summarizer
from agent.gap_checker   import GapChecker
from agent.synthesizer   import Synthesizer
from agent.output_writer import save_report
from tools.web_search    import WebSearchTool
import config


class ResearchOrchestrator:
    def __init__(self):
        self.planner    = Planner()
        self.searcher   = WebSearchTool()
        self.scorer     = SourceScorer()
        self.summarizer = Summarizer()
        self.gap_checker = GapChecker()
        self.synthesizer = Synthesizer()

    def _research_sub_question(
        self,
        sub_question: str,
        question_idx: int,
        total: int,
    ) -> list[dict]:
        """
        Full pipeline for one sub-question:
        Search → Score → Summarize → (loop if gap found)
        """
        print(f"\n{'─'*56}")
        print(f"[{question_idx}/{total}] {sub_question}")
        print(f"{'─'*56}")

        query = sub_question  # initial query = the sub-question itself
        all_findings = []

        for loop_i in range(config.MAX_SEARCH_LOOPS + 1):
            if loop_i > 0:
                print(f"\n   🔁 Re-search loop #{loop_i}")

            # ── STEP 2: Search ──────────────────────────────────
            print(f"   🌐 Searching: '{query[:70]}'")
            try:
                raw_sources = self.searcher.search(query)
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
                break

            print(f"   → {len(raw_sources)} results returned")

            # ── STEP 3: Score & Filter ──────────────────────────
            good_sources = self.scorer.score_and_filter(raw_sources, sub_question)

            # ── STEP 4: Summarize ───────────────────────────────
            print(f"   📖 Extracting findings from {len(good_sources)} sources...")
            new_findings = self.summarizer.extract_all(good_sources, sub_question)
            print(f"   → {len(new_findings)} relevant findings extracted")

            all_findings.extend(new_findings)

            # ── STEP 5: Gap check ───────────────────────────────
            if self.gap_checker.has_enough_findings(all_findings):
                print(f"   ✅ Coverage satisfied ({len(all_findings)} findings)")
                break
            elif loop_i < config.MAX_SEARCH_LOOPS:
                query = self.gap_checker.refine_query(query, sub_question)
            else:
                print(f"   ⚠️  Max loops reached. Proceeding with {len(all_findings)} findings.")

        return all_findings

    async def run(self, topic: str, max_sub_questions: int | None = None) -> str:
        """Run the full research agent pipeline."""

        # ── STEP 1: Plan ────────────────────────────────────────
        plan = self.planner.decompose(topic, max_sub_questions=max_sub_questions)

        # ── STEPS 2–5: Research each sub-question ───────────────
        print(f"\n\n🔬 Researching {len(plan['sub_questions'])} sub-questions...")
        max_parallel = max(1, min(config.MAX_PARALLEL_RESEARCH, len(plan["sub_questions"])))
        print(f"   Parallel workers: {max_parallel}")
        all_findings: dict[str, list[dict]] = {}

        semaphore = asyncio.Semaphore(max_parallel)

        async def run_one(i: int, question: str) -> tuple[str, list[dict]]:
            async with semaphore:
                findings = await asyncio.to_thread(
                    self._research_sub_question,
                    question,
                    i,
                    len(plan["sub_questions"]),
                )
                return question, findings

        tasks = [
            run_one(i, question)
            for i, question in enumerate(plan["sub_questions"], 1)
        ]
        for question, findings in await asyncio.gather(*tasks):
            all_findings[question] = findings

        # ── STEP 6: Synthesize ───────────────────────────────────
        report_md = self.synthesizer.write_report(plan, all_findings)

        # ── STEP 7: Save ─────────────────────────────────────────
        print("\n💾 [DELIVER] Saving report...")
        report_path = save_report(plan["title"], report_md, all_findings)

        return report_path
