"""
Local web UI for the AI Research Agent.

Run with:
    python web_app.py
"""

import asyncio
import contextlib
import io
import json
import os
import threading
import traceback
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from agent.orchestrator import ResearchOrchestrator
import config


HOST = "127.0.0.1"
PORT = 8000
ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = (ROOT / config.OUTPUT_DIR).resolve()
RUN_LOCK = threading.Lock()


def output_links(report_path: str) -> dict:
    report = (ROOT / report_path).resolve()
    base = report.with_suffix("")
    files = {
        "markdown": report,
        "html": base.with_suffix(".html"),
        "json": Path(f"{base}_findings.json"),
    }
    return {
        key: f"/output/{path.name}"
        for key, path in files.items()
        if path.exists() and path.is_file()
    }


def run_agent(topic: str) -> dict:
    if not RUN_LOCK.acquire(blocking=False):
        return {
            "ok": False,
            "error": "Another research run is already in progress. Please wait for it to finish.",
        }

    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            orchestrator = ResearchOrchestrator()
            report_path = asyncio.run(orchestrator.run(topic))

        return {
            "ok": True,
            "report_path": report_path,
            "links": output_links(report_path),
            "log": buffer.getvalue(),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "log": buffer.getvalue() + "\n" + traceback.format_exc(),
        }
    finally:
        RUN_LOCK.release()


class ResearchAgentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[web] {self.address_string()} - {format % args}")

    def send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path.startswith("/output/"):
            name = unquote(self.path.removeprefix("/output/")).split("?", 1)[0]
            path = (OUTPUT_DIR / name).resolve()
            if OUTPUT_DIR not in path.parents or not path.exists() or not path.is_file():
                self.send_error(404, "Report not found")
                return
            self.path = f"/{config.OUTPUT_DIR}/{path.name}"
            return super().do_GET()

        self.send_error(404, "Not found")

    def do_POST(self):
        if self.path != "/api/run":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(400, {"ok": False, "error": "Invalid JSON payload."})
            return

        topic = str(payload.get("topic", "")).strip()
        if not topic:
            self.send_json(400, {"ok": False, "error": "Please enter a research topic."})
            return

        self.send_json(200, run_agent(topic))


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ResearchAgent - Battle Plan</title>
  <style>
    :root {
      --bg: #f8f7f4;
      --card: #fffefd;
      --ink: #171717;
      --muted: #7a7a76;
      --line: #ddd9d2;
      --green: #047869;
      --green-soft: #e5f4f1;
      --red: #d92d20;
      --red-soft: #fff0ed;
      --amber: #9a6a00;
      --amber-soft: #fff5d7;
      --blue: #315db6;
      --blue-soft: #edf3ff;
      --violet: #6d4fd1;
      --violet-soft: #f2eeff;
      --shadow: 0 10px 26px rgba(22, 20, 16, .05);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    button, textarea { font: inherit; }
    a { color: inherit; text-decoration: none; }
    .page {
      width: min(1180px, calc(100% - 44px));
      margin: 0 auto;
      padding: 34px 0 46px;
    }
    .topline {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 20px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 0 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--card);
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .pill.green { color: var(--green); border-color: #8bd6cb; background: var(--green-soft); }
    .pill.red { color: var(--red); border-color: #ffc5bd; background: var(--red-soft); }
    .pill.amber { color: var(--amber); border-color: #efd382; background: var(--amber-soft); }
    h1 {
      max-width: 640px;
      margin: 0;
      font-size: clamp(34px, 5vw, 52px);
      line-height: 1.04;
      letter-spacing: 0;
    }
    h1 span { color: var(--green); }
    .sub {
      margin: 14px 0 34px;
      color: var(--muted);
      font-size: 16px;
    }
    .score-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
      margin-bottom: 34px;
    }
    .score-card, .panel, .gap, .week, .advantage, .runner {
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--card);
      box-shadow: var(--shadow);
    }
    .score-card {
      padding: 22px 22px 18px;
      text-align: center;
    }
    .score-card small {
      display: block;
      color: #858581;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .score {
      margin: 8px 0 6px;
      font-size: 44px;
      line-height: 1;
      font-weight: 500;
      color: var(--tone);
    }
    .meter {
      height: 8px;
      border-radius: 999px;
      overflow: hidden;
      background: #ece9e3;
    }
    .meter span {
      display: block;
      width: var(--width);
      height: 100%;
      border-radius: inherit;
      background: var(--tone);
    }
    .score-card p {
      margin: 8px 0 0;
      color: #84817c;
      font-size: 12px;
    }
    .compare {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-bottom: 40px;
    }
    .panel { padding: 22px; }
    .section-label {
      margin: 0 0 18px;
      color: var(--label);
      font-size: 13px;
      font-weight: 900;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .checklist {
      display: grid;
      gap: 0;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .checklist li {
      display: grid;
      grid-template-columns: 12px 1fr;
      gap: 10px;
      padding: 9px 0;
      border-bottom: 1px solid #ece8e1;
      color: #44423f;
      font-size: 14px;
    }
    .checklist li:last-child { border-bottom: 0; }
    .dot {
      width: 8px;
      height: 8px;
      margin-top: 7px;
      border-radius: 50%;
      background: var(--dot);
    }
    .block-title {
      margin: 0 0 18px;
      color: #7d7b76;
      font-size: 13px;
      font-weight: 900;
      letter-spacing: .13em;
      text-transform: uppercase;
    }
    .gap-list {
      display: grid;
      gap: 14px;
      margin-bottom: 44px;
    }
    .gap {
      display: grid;
      grid-template-columns: 56px 1fr auto;
      gap: 18px;
      align-items: start;
      padding: 20px;
    }
    .gap-icon {
      width: 42px;
      height: 42px;
      display: grid;
      place-items: center;
      border-radius: 12px;
      color: var(--tone);
      background: var(--soft);
    }
    .gap h3, .week h3 {
      margin: 0 0 5px;
      font-size: 16px;
      line-height: 1.3;
    }
    .gap p, .week p {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }
    .priority {
      display: grid;
      justify-items: end;
      gap: 6px;
      color: #8d8880;
      font-size: 12px;
      white-space: nowrap;
    }
    .priority span {
      padding: 3px 10px;
      border-radius: 999px;
      background: var(--soft);
      color: var(--tone);
      font-weight: 900;
      letter-spacing: .06em;
      text-transform: uppercase;
    }
    .weeks {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      margin-bottom: 44px;
    }
    .week {
      padding: 22px;
      min-height: 190px;
    }
    .week small {
      display: block;
      margin-bottom: 12px;
      color: #96918a;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .tag {
      display: inline-flex;
      align-items: center;
      margin-top: 20px;
      min-height: 26px;
      padding: 0 11px;
      border-radius: 999px;
      background: var(--soft);
      color: var(--tone);
      font-size: 12px;
      font-weight: 800;
    }
    .advantages {
      display: grid;
      gap: 14px;
      margin-bottom: 34px;
    }
    .advantage {
      display: grid;
      grid-template-columns: 18px 1fr;
      gap: 14px;
      padding: 20px 24px;
      border-color: #88d8cd;
      background: #e9f8f5;
      color: #074f47;
    }
    .advantage strong { color: #05433d; }
    .advantage p {
      margin: 0;
      color: #0d5c54;
      font-size: 14px;
    }
    .runner {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 18px;
      align-items: center;
      padding: 24px;
      background: #111;
      color: white;
      border-color: #111;
    }
    .runner h2 {
      margin: 0 0 4px;
      font-size: 20px;
      letter-spacing: 0;
    }
    .runner p {
      margin: 0;
      color: #b9b9b9;
      font-size: 14px;
    }
    .run-form {
      grid-column: 1 / -1;
      display: none;
      grid-template-columns: 1fr auto;
      gap: 12px;
      margin-top: 4px;
    }
    .run-form.show { display: grid; }
    textarea {
      width: 100%;
      min-height: 84px;
      resize: vertical;
      border: 1px solid #333;
      border-radius: 12px;
      padding: 14px;
      outline: none;
      background: #1b1b1b;
      color: white;
    }
    textarea:focus { border-color: #79d3c8; }
    .btn {
      min-height: 48px;
      border: 1px solid #3c3c3c;
      border-radius: 12px;
      padding: 0 18px;
      background: transparent;
      color: white;
      cursor: pointer;
      font-weight: 800;
    }
    .btn.primary {
      background: white;
      color: #111;
      border-color: white;
    }
    .btn:disabled {
      opacity: .7;
      cursor: wait;
    }
    .result {
      display: none;
      grid-column: 1 / -1;
      padding-top: 8px;
    }
    .result.show { display: block; }
    .links {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 12px 0;
    }
    .links a {
      padding: 8px 12px;
      border-radius: 999px;
      background: #e9f8f5;
      color: #07564e;
      font-size: 13px;
      font-weight: 800;
    }
    pre {
      max-height: 260px;
      overflow: auto;
      margin: 0;
      padding: 14px;
      border-radius: 12px;
      background: #050505;
      color: #d7fff9;
      font-size: 12px;
      white-space: pre-wrap;
    }
    .error { color: #ffb4aa; }

    @media (max-width: 820px) {
      .score-grid, .compare, .weeks { grid-template-columns: 1fr; }
      .gap { grid-template-columns: 46px 1fr; }
      .priority { grid-column: 2; justify-items: start; }
      .runner { grid-template-columns: 1fr; }
      .run-form { grid-template-columns: 1fr; }
    }
    @media (max-width: 520px) {
      .page { width: min(100% - 28px, 1180px); padding-top: 22px; }
      .gap { grid-template-columns: 1fr; }
      .priority { grid-column: 1; }
    }
  </style>
</head>
<body>
  <main class="page">
    <div class="topline">
      <span class="pill green">Your Project</span>
      <span class="pill red">Synapse AI</span>
      <span class="pill amber">After Upgrades</span>
    </div>

    <h1>How to <span>outbuild Synapse AI</span> with your research agent</h1>
    <p class="sub">A practical upgrade map for this repo: what exists now, what is missing, and what to build next.</p>

    <section class="score-grid" aria-label="Project comparison scores">
      <article class="score-card" style="--tone: var(--green); --width: 64%">
        <small>Your project now</small>
        <div class="score">6.5</div>
        <div class="meter"><span></span></div>
        <p>Clean base, simple UI, working agent</p>
      </article>
      <article class="score-card" style="--tone: var(--red); --width: 84%">
        <small>Synapse AI now</small>
        <div class="score">8.5</div>
        <div class="meter"><span></span></div>
        <p>Strong architecture and deployment story</p>
      </article>
      <article class="score-card" style="--tone: var(--amber); --width: 92%">
        <small>Your project v2</small>
        <div class="score">9.2</div>
        <div class="meter"><span></span></div>
        <p>Reachable with focused upgrades</p>
      </article>
    </section>

    <section class="compare" aria-label="Current comparison">
      <article class="panel" style="--label: var(--green)">
        <h2 class="section-label">You have</h2>
        <ul class="checklist">
          <li><span class="dot" style="--dot:#24b65a"></span><span>Clean modular Python architecture</span></li>
          <li><span class="dot" style="--dot:#24b65a"></span><span>Working agent loop with gap checking</span></li>
          <li><span class="dot" style="--dot:#24b65a"></span><span>Source scoring based on relevance and recency</span></li>
          <li><span class="dot" style="--dot:#24b65a"></span><span>Light dashboard UI wired to the backend</span></li>
          <li><span class="dot" style="--dot:#24b65a"></span><span>Groq + Tavily free-stack implementation</span></li>
          <li><span class="dot" style="--dot:#ef4444"></span><span>No LangGraph orchestration yet</span></li>
          <li><span class="dot" style="--dot:#ef4444"></span><span>No vector memory for past findings</span></li>
          <li><span class="dot" style="--dot:#ef4444"></span><span>No FastAPI streaming endpoint yet</span></li>
          <li><span class="dot" style="--dot:#ef4444"></span><span>No deployed live demo URL</span></li>
        </ul>
      </article>
      <article class="panel" style="--label: var(--red)">
        <h2 class="section-label">Synapse has</h2>
        <ul class="checklist">
          <li><span class="dot" style="--dot:#24b65a"></span><span>LangGraph multi-agent workflow</span></li>
          <li><span class="dot" style="--dot:#24b65a"></span><span>Vector memory with ChromaDB</span></li>
          <li><span class="dot" style="--dot:#24b65a"></span><span>FastAPI plus SSE progress streaming</span></li>
          <li><span class="dot" style="--dot:#24b65a"></span><span>Next.js frontend deployed publicly</span></li>
          <li><span class="dot" style="--dot:#24b65a"></span><span>Docker, Railway, and Vercel story</span></li>
          <li><span class="dot" style="--dot:#ef4444"></span><span>More complexity to explain in interviews</span></li>
          <li><span class="dot" style="--dot:#ef4444"></span><span>No clear evaluation metrics layer</span></li>
          <li><span class="dot" style="--dot:#ef4444"></span><span>No PDF export highlighted as shipped</span></li>
          <li><span class="dot" style="--dot:#f59e0b"></span><span>You can own the simpler, clearer codebase</span></li>
        </ul>
      </article>
    </section>

    <h2 class="block-title">Critical gaps to fill - prioritized</h2>
    <section class="gap-list" aria-label="Prioritized upgrade list">
      <article class="gap" style="--tone:var(--red);--soft:var(--red-soft)"><div class="gap-icon">1</div><div><h3>Build commit history from now</h3><p>Make small real commits for each upgrade: UI polish, FastAPI wrapper, streaming, memory, deployment, and docs.</p></div><div class="priority"><span>Critical</span>1 day</div></article>
      <article class="gap" style="--tone:var(--blue);--soft:var(--blue-soft)"><div class="gap-icon">2</div><div><h3>FastAPI backend with progress streaming</h3><p>Wrap the orchestrator in /api/run and /api/stream endpoints so the frontend can show live node progress.</p></div><div class="priority"><span>Critical</span>2-3 days</div></article>
      <article class="gap" style="--tone:var(--violet);--soft:var(--violet-soft)"><div class="gap-icon">3</div><div><h3>ChromaDB vector memory</h3><p>Embed findings after each run and retrieve related findings across past reports for follow-up research.</p></div><div class="priority"><span>Critical</span>2 days</div></article>
      <article class="gap" style="--tone:var(--red);--soft:var(--red-soft)"><div class="gap-icon">4</div><div><h3>LangGraph refactor</h3><p>Turn planner, searcher, scorer, summarizer, gap checker, and synthesizer into graph nodes with conditional edges.</p></div><div class="priority"><span>Critical</span>3-5 days</div></article>
      <article class="gap" style="--tone:var(--amber);--soft:var(--amber-soft)"><div class="gap-icon">5</div><div><h3>Async parallel research</h3><p>Research sub-questions concurrently and show benchmark numbers against the current sequential pipeline.</p></div><div class="priority"><span>High</span>1 day</div></article>
      <article class="gap" style="--tone:var(--green);--soft:var(--green-soft)"><div class="gap-icon">6</div><div><h3>Evaluation metrics dashboard</h3><p>Add source credibility, citation density, unsupported-claim warnings, and confidence score per finding.</p></div><div class="priority"><span>High</span>2 days</div></article>
      <article class="gap" style="--tone:var(--blue);--soft:var(--blue-soft)"><div class="gap-icon">7</div><div><h3>Deployment path</h3><p>Deploy the backend to Railway or Render and the frontend to Vercel, then add live demo links to README.</p></div><div class="priority"><span>High</span>Half day</div></article>
      <article class="gap" style="--tone:var(--amber);--soft:var(--amber-soft)"><div class="gap-icon">8</div><div><h3>PDF export for reports</h3><p>Add clean PDF export with citations so generated reports are presentation-ready.</p></div><div class="priority"><span>Medium</span>1 day</div></article>
    </section>

    <h2 class="block-title">4-week execution plan</h2>
    <section class="weeks" aria-label="Four week plan">
      <article class="week" style="--tone:var(--red);--soft:var(--red-soft)"><small>Week 01</small><h3>Fix the fundamentals</h3><p>Refactor UI, create 20+ meaningful commits, add FastAPI run endpoints, and prepare deployment configs.</p><span class="tag">Urgent</span></article>
      <article class="week" style="--tone:var(--amber);--soft:var(--amber-soft)"><small>Week 02</small><h3>Add LangGraph + ChromaDB</h3><p>Convert the pipeline into graph nodes and store extracted findings in vector memory.</p><span class="tag">Architecture</span></article>
      <article class="week" style="--tone:var(--blue);--soft:var(--blue-soft)"><small>Week 03</small><h3>Evaluation system + PDF export</h3><p>Build a metrics panel, unsupported-claim checks, PDF export, and benchmark screenshots.</p><span class="tag">Differentiator</span></article>
      <article class="week" style="--tone:var(--violet);--soft:var(--violet-soft)"><small>Week 04</small><h3>Polish + job materials</h3><p>Record a demo, update README, add architecture diagrams, and publish a technical write-up.</p><span class="tag">Visibility</span></article>
    </section>

    <h2 class="block-title">Your actual advantages over Synapse AI</h2>
    <section class="advantages" aria-label="Advantages">
      <article class="advantage"><span>+</span><p><strong>You can explain every line.</strong> Your stack is smaller, so interview explanations are clearer and more credible.</p></article>
      <article class="advantage"><span>+</span><p><strong>Async research is a real edge.</strong> Parallel sub-question search can make your project measurably faster.</p></article>
      <article class="advantage"><span>+</span><p><strong>Evaluation metrics are underbuilt territory.</strong> A quality layer can make your project feel more research-grade.</p></article>
      <article class="advantage"><span>+</span><p><strong>PDF export is practical.</strong> Recruiters and users understand a polished report artifact immediately.</p></article>
    </section>

    <section class="runner">
      <div>
        <h2>Ready to run the current agent?</h2>
        <p>Use the working Groq + Tavily pipeline now, then build the v2 upgrades from this roadmap.</p>
      </div>
      <button id="toggle-form" class="btn">Start a research run -></button>
      <form id="run-form" class="run-form">
        <textarea id="topic" name="topic" placeholder="Example: AI engineer skills freshers need in 2026" required></textarea>
        <button id="run-button" class="btn primary" type="submit">Run agent</button>
      </form>
      <div id="result" class="result" aria-live="polite"></div>
    </section>
  </main>

  <script>
    const toggle = document.querySelector("#toggle-form");
    const form = document.querySelector("#run-form");
    const topic = document.querySelector("#topic");
    const button = document.querySelector("#run-button");
    const result = document.querySelector("#result");

    toggle.addEventListener("click", () => {
      form.classList.toggle("show");
      if (form.classList.contains("show")) topic.focus();
    });

    const escapeHtml = (value) => value.replace(/[&<>]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[ch]));

    function renderRunning() {
      result.className = "result show";
      result.innerHTML = "<strong>Agent is running...</strong><p>This can take a minute or two while the agent searches, scores, summarizes, and writes the report.</p>";
    }

    function renderResult(data) {
      const log = escapeHtml(data.log || "");
      if (!data.ok) {
        result.className = "result show";
        result.innerHTML = `<strong class="error">Run failed</strong><p class="error">${data.error || "Unknown error"}</p><pre>${log}</pre>`;
        return;
      }

      const links = Object.entries(data.links || {})
        .map(([label, href]) => `<a href="${href}" target="_blank" rel="noreferrer">${label} report</a>`)
        .join("");

      result.className = "result show";
      result.innerHTML = `<strong>Report generated</strong><div class="links">${links}</div><pre>${log}</pre>`;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const value = topic.value.trim();
      if (!value) return;

      button.disabled = true;
      button.textContent = "Running...";
      renderRunning();

      try {
        const response = await fetch("/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic: value }),
        });
        renderResult(await response.json());
      } catch (error) {
        renderResult({ ok: false, error: error.message });
      } finally {
        button.disabled = false;
        button.textContent = "Run agent";
      }
    });
  </script>
</body>
</html>
"""


def main():
    os.chdir(ROOT)
    OUTPUT_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), ResearchAgentHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"ResearchAgent UI running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
