"""
AI Research Agent — main entry point
Free stack: Groq (LLaMA 3.3-70B) + Tavily Search
"""

import asyncio
import sys
from agent.orchestrator import ResearchOrchestrator

def main():
    print("\n" + "="*60)
    print("  🔬 AI Research Agent")
    print("  Powered by Groq (LLaMA 3) + Tavily Search (Free)")
    print("="*60 + "\n")

    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = input("Enter your research topic: ").strip()
        if not topic:
            print("No topic provided. Exiting.")
            sys.exit(1)

    orchestrator = ResearchOrchestrator()
    report_path = asyncio.run(orchestrator.run(topic))

    print(f"\n✅ Report saved to: {report_path}")
    print("="*60)

if __name__ == "__main__":
    main()
