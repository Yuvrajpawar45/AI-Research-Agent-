# AI Research Agent v2 Upgrade Plan

This roadmap is based on the comparison against Synapse AI and focuses on job-ready engineering signals.

| Area | Current Status | Upgrade Value |
| --- | --- | --- |
| LangGraph workflow | Added graph package with planner, search, scorer, summarizer, gap checker, synthesizer, and deliver nodes | Shows modern agent orchestration |
| FastAPI backend | Added `/api/health`, `/api/run`, and `/api/stream` | Makes the agent usable as a backend service |
| SSE streaming | Added streaming endpoint for graph progress updates | Gives the project a production-style AI app interface |
| Parallel research | Added configurable concurrent sub-question research in the classic orchestrator | Differentiates from sequential research agents |
| Evaluation metrics | Added generated quality report with source diversity, citation density, confidence score, and risk flags | Turns the project into a measurable research system |
| Deployment files | Added Procfile and runtime metadata | Prepares backend deployment on Railway/Render |

## Next Highest-Impact Work

| Priority | Task | Why It Matters |
| --- | --- | --- |
| Critical | Commit history with small meaningful commits | Recruiters can see real development progress |
| Critical | Deploy backend and frontend/live UI | Recruiters can verify the project instantly |
| High | Add ChromaDB or FAISS memory | Shows real RAG and semantic retrieval skills |
| High | Show quality metrics in the UI | Makes the evaluator visible, not hidden in JSON |
| Medium | Add PDF export | Useful product feature and clear resume bullet |
| Medium | Add tests for scoring, evaluation, and graph routing | Proves engineering maturity |

## Resume Positioning

Use this phrasing only after the v2 code is committed and the API runs:

> Built an autonomous AI research agent with LangGraph orchestration, FastAPI streaming, parallel web research, source scoring, and built-in report quality evaluation.
