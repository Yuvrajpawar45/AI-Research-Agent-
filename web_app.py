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
        "findings": Path(f"{base}_findings.json"),
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
  <title>AI Research Agent</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #151922;
      --muted: #687083;
      --line: #dde2ea;
      --green: #0f766e;
      --green-dark: #115e59;
      --green-soft: #e7f4f1;
      --orange: #ea580c;
      --blue: #2563eb;
      --shadow: 0 18px 45px rgba(31, 41, 55, .08);
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
    .app {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 290px 1fr;
    }
    aside {
      position: sticky;
      top: 0;
      height: 100vh;
      padding: 26px;
      border-right: 1px solid var(--line);
      background: #fbfcfd;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 34px;
      font-size: 19px;
      font-weight: 850;
    }
    .logo {
      width: 40px;
      height: 40px;
      display: grid;
      place-items: center;
      border-radius: 12px;
      background: var(--green);
      color: white;
      box-shadow: 0 12px 28px rgba(15, 118, 110, .22);
    }
    .brand span span { color: var(--green); }
    .nav-title {
      margin: 0 0 10px;
      color: #8a92a3;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .1em;
      text-transform: uppercase;
    }
    .steps {
      display: grid;
      gap: 10px;
      margin-bottom: 28px;
    }
    .step {
      display: grid;
      grid-template-columns: 30px 1fr;
      gap: 10px;
      align-items: center;
      padding: 12px;
      border: 1px solid transparent;
      border-radius: 14px;
      color: #465063;
      background: transparent;
    }
    .step strong {
      display: block;
      font-size: 14px;
    }
    .step small {
      color: #8991a1;
      font-size: 12px;
    }
    .step-number {
      width: 30px;
      height: 30px;
      display: grid;
      place-items: center;
      border-radius: 10px;
      background: #eef1f5;
      color: #687083;
      font-size: 12px;
      font-weight: 850;
    }
    .step.active {
      border-color: #b8ddd7;
      background: var(--green-soft);
      color: var(--green-dark);
    }
    .step.active .step-number {
      background: var(--green);
      color: white;
    }
    .stack {
      margin-top: auto;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: white;
    }
    .stack p {
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 13px;
    }
    .stack-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .tag {
      padding: 5px 9px;
      border-radius: 999px;
      background: #f1f3f6;
      color: #4b5565;
      font-size: 12px;
      font-weight: 700;
    }
    main {
      padding: 34px;
    }
    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 18px;
      margin-bottom: 30px;
    }
    .topbar h1 {
      margin: 0;
      font-size: clamp(30px, 5vw, 54px);
      line-height: 1.05;
      letter-spacing: 0;
    }
    .topbar p {
      max-width: 720px;
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 17px;
    }
    .status {
      flex: none;
      padding: 10px 14px;
      border: 1px solid #b8ddd7;
      border-radius: 999px;
      background: var(--green-soft);
      color: var(--green-dark);
      font-size: 13px;
      font-weight: 800;
    }
    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(340px, .65fr);
      gap: 24px;
      align-items: start;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--panel);
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .panel-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      padding: 20px 22px;
      border-bottom: 1px solid var(--line);
    }
    .panel-head h2 {
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
    }
    .panel-head span {
      color: var(--muted);
      font-size: 13px;
    }
    form {
      padding: 22px;
    }
    label {
      display: block;
      margin-bottom: 10px;
      color: #374151;
      font-size: 14px;
      font-weight: 800;
    }
    textarea {
      width: 100%;
      min-height: 180px;
      resize: vertical;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 16px;
      outline: none;
      color: var(--ink);
      background: #fff;
    }
    textarea:focus {
      border-color: #78c9bf;
      box-shadow: 0 0 0 4px rgba(15, 118, 110, .1);
    }
    .actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      margin-top: 16px;
      flex-wrap: wrap;
    }
    .hint {
      color: var(--muted);
      font-size: 13px;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 9px;
      min-height: 48px;
      padding: 0 18px;
      border: 0;
      border-radius: 14px;
      background: var(--green);
      color: white;
      font-weight: 850;
      cursor: pointer;
      box-shadow: 0 14px 28px rgba(15, 118, 110, .18);
    }
    .btn:hover { background: var(--green-dark); }
    .btn:disabled {
      opacity: .72;
      cursor: wait;
    }
    .examples {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      padding: 0 22px 22px;
    }
    .example {
      min-height: 64px;
      text-align: left;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fbfcfd;
      color: #344054;
      cursor: pointer;
    }
    .example strong {
      display: block;
      margin-bottom: 3px;
      color: var(--green-dark);
      font-size: 12px;
    }
    .cards {
      display: grid;
      gap: 14px;
    }
    .mini-card {
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: white;
      box-shadow: 0 10px 24px rgba(31, 41, 55, .04);
    }
    .mini-card h3 {
      margin: 0 0 6px;
      font-size: 16px;
    }
    .mini-card p {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }
    .metric {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
    }
    .bar {
      width: 110px;
      height: 7px;
      border-radius: 999px;
      overflow: hidden;
      background: #edf0f4;
    }
    .bar span {
      display: block;
      height: 100%;
      width: var(--value);
      border-radius: inherit;
      background: var(--color);
    }
    .result {
      display: none;
      margin-top: 24px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: white;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .result.show { display: block; }
    .result-body { padding: 20px 22px; }
    .result strong {
      display: block;
      margin-bottom: 12px;
      font-size: 17px;
    }
    .links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 14px;
    }
    .links a {
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--green-soft);
      color: var(--green-dark);
      font-size: 13px;
      font-weight: 800;
      text-decoration: none;
    }
    pre {
      max-height: 320px;
      overflow: auto;
      margin: 0;
      padding: 14px;
      border-radius: 14px;
      background: #111827;
      color: #d1fae5;
      font-size: 12px;
      white-space: pre-wrap;
    }
    .error { color: #b42318; }

    @media (max-width: 980px) {
      .app { grid-template-columns: 1fr; }
      aside {
        position: static;
        height: auto;
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }
      .steps { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
      main, aside { padding: 20px; }
      .topbar { align-items: flex-start; flex-direction: column; }
      .steps, .examples { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <div class="brand">
        <div class="logo" aria-hidden="true">
          <svg width="21" height="21" viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="16" rx="3" stroke="currentColor" stroke-width="2"/><path d="M9 9h6v6H9zM15 2v2M15 20v2M9 2v2M9 20v2M2 9h2M2 15h2M20 9h2M20 15h2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </div>
        <span>Research<span>Agent</span></span>
      </div>

      <p class="nav-title">Pipeline</p>
      <div class="steps">
        <div class="step active"><div class="step-number">01</div><div><strong>Plan</strong><small>Split topic into questions</small></div></div>
        <div class="step"><div class="step-number">02</div><div><strong>Search</strong><small>Collect web sources</small></div></div>
        <div class="step"><div class="step-number">03</div><div><strong>Score</strong><small>Keep stronger evidence</small></div></div>
        <div class="step"><div class="step-number">04</div><div><strong>Summarize</strong><small>Extract key findings</small></div></div>
        <div class="step"><div class="step-number">05</div><div><strong>Synthesize</strong><small>Write cited report</small></div></div>
      </div>

      <div class="stack">
        <p>Free stack used by this project.</p>
        <div class="stack-tags">
          <span class="tag">Groq</span>
          <span class="tag">Tavily</span>
          <span class="tag">Python</span>
          <span class="tag">Markdown</span>
        </div>
      </div>
    </aside>

    <main>
      <div class="topbar">
        <div>
          <h1>Research console for autonomous reports</h1>
          <p>Enter a topic and let the agent plan, search, score, summarize, and generate cited Markdown, HTML, and findings JSON.</p>
        </div>
        <div class="status">Local UI ready</div>
      </div>

      <div class="grid">
        <section class="panel">
          <div class="panel-head">
            <h2>Start a research run</h2>
            <span>Usually takes 1-3 minutes</span>
          </div>
          <form id="run-form">
            <label for="topic">Research topic</label>
            <textarea id="topic" name="topic" placeholder="Example: Impact of AI on healthcare delivery in India" required></textarea>
            <div class="actions">
              <span class="hint">Runs with your existing Groq + Tavily backend.</span>
              <button id="run-button" class="btn" type="submit">
                Run agent
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M5 12h14m-7-7 7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </button>
            </div>
          </form>
          <div class="examples">
            <button class="example" type="button"><strong>Healthcare</strong>Impact of AI on healthcare delivery in India</button>
            <button class="example" type="button"><strong>Energy</strong>Future of nuclear energy in India</button>
            <button class="example" type="button"><strong>Careers</strong>AI engineer skills freshers need in 2026</button>
            <button class="example" type="button"><strong>Climate</strong>Climate adaptation strategies for coastal cities</button>
          </div>
        </section>

        <section class="cards" aria-label="Agent capabilities">
          <article class="mini-card">
            <h3>Source-aware output</h3>
            <p>Reports include citations from the gathered sources.</p>
            <div class="metric"><span>Citation flow</span><div class="bar"><span style="--value:80%;--color:var(--green)"></span></div></div>
          </article>
          <article class="mini-card">
            <h3>Gap checking loop</h3>
            <p>The agent can refine the query when evidence is thin.</p>
            <div class="metric"><span>Autonomy</span><div class="bar"><span style="--value:68%;--color:var(--orange)"></span></div></div>
          </article>
          <article class="mini-card">
            <h3>Multiple exports</h3>
            <p>Each run creates Markdown, HTML, and findings JSON files.</p>
            <div class="metric"><span>Export coverage</span><div class="bar"><span style="--value:92%;--color:var(--blue)"></span></div></div>
          </article>
        </section>
      </div>

      <section id="result" class="result" aria-live="polite"></section>
    </main>
  </div>

  <script>
    const form = document.querySelector("#run-form");
    const topic = document.querySelector("#topic");
    const button = document.querySelector("#run-button");
    const result = document.querySelector("#result");

    document.querySelectorAll(".example").forEach((example) => {
      example.addEventListener("click", () => {
        topic.value = example.textContent.replace(/Healthcare|Energy|Careers|Climate/g, "").trim();
        topic.focus();
      });
    });

    const escapeHtml = (value) => value.replace(/[&<>]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[ch]));

    function renderRunning() {
      result.className = "result show";
      result.innerHTML = '<div class="panel-head"><h2>Research in progress</h2><span>Searching and writing</span></div><div class="result-body"><strong>Agent is running...</strong><p class="hint">Keep this page open while the report is generated.</p></div>';
    }

    function renderResult(data) {
      const log = escapeHtml(data.log || "");
      if (!data.ok) {
        result.className = "result show";
        result.innerHTML = `<div class="panel-head"><h2 class="error">Run failed</h2><span>Error</span></div><div class="result-body"><strong class="error">${data.error || "Unknown error"}</strong><pre>${log}</pre></div>`;
        return;
      }

      const links = Object.entries(data.links || {})
        .map(([label, href]) => `<a href="${href}" target="_blank" rel="noreferrer">${label} report</a>`)
        .join("");

      result.className = "result show";
      result.innerHTML = `<div class="panel-head"><h2>Report generated</h2><span>Output ready</span></div><div class="result-body"><strong>Your research report is ready.</strong><div class="links">${links}</div><pre>${log}</pre></div>`;
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
        button.innerHTML = 'Run agent <svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M5 12h14m-7-7 7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
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
    print(f"AI Research Agent UI running at {url}")
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
