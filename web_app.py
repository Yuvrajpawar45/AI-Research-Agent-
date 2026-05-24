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
  <title>Research Agent - Autonomous Research Workspace</title>
  <style>
    :root {
      --brand: #0f766e;
      --brand-dark: #115e59;
      --brand-soft: #e6f4f1;
      --accent: #f97316;
      --accent-soft: #fff3e8;
      --ink: #1f2933;
      --muted: #697586;
      --line: #ded8cd;
      --surface: #fffefb;
      --panel: #f6f3ee;
      --footer: #1f2933;
      --shadow: 0 18px 40px rgba(62, 53, 42, 0.09);
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      background: #fbfaf7;
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }
    a { color: inherit; text-decoration: none; }
    .nav {
      position: fixed;
      inset: 0 0 auto;
      z-index: 20;
      height: 64px;
      background: rgba(251, 250, 247, 0.9);
      border-bottom: 1px solid rgba(222, 216, 205, 0.85);
      backdrop-filter: blur(18px);
    }
    .nav-inner, .wrap {
      width: min(1120px, calc(100% - 48px));
      margin: 0 auto;
    }
    .nav-inner {
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }
    .brand {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      font-weight: 800;
      font-size: 18px;
    }
    .mark {
      width: 34px;
      height: 34px;
      border-radius: 10px;
      background: var(--brand);
      color: white;
      display: grid;
      place-items: center;
      box-shadow: 0 12px 24px rgba(15, 118, 110, 0.22);
    }
    .brand span span { color: var(--brand); }
    .nav-links {
      display: flex;
      align-items: center;
      gap: 30px;
      color: #5f6c7b;
      font-size: 14px;
      font-weight: 650;
    }
    .nav-links a:hover { color: var(--brand); }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 42px;
      padding: 0 18px;
      border-radius: 11px;
      border: 1px solid transparent;
      background: var(--brand);
      color: #fff;
      font: inherit;
      font-weight: 750;
      cursor: pointer;
      box-shadow: 0 14px 26px rgba(15, 118, 110, 0.2);
    }
    .btn:hover { background: var(--brand-dark); }
    .btn.secondary {
      background: white;
      color: #334155;
      border-color: var(--line);
      box-shadow: 0 12px 24px rgba(15, 23, 42, 0.04);
    }
    .btn:disabled {
      opacity: .72;
      cursor: wait;
    }
    .hero {
      position: relative;
      min-height: 100vh;
      display: grid;
      align-items: center;
      overflow: hidden;
      padding: 116px 0 84px;
    }
    .hero::before {
      content: "";
      position: absolute;
      inset: 0;
      z-index: -2;
      background:
        linear-gradient(180deg, rgba(255,255,255,.72), rgba(251,250,247,.95)),
        radial-gradient(circle at 12% 18%, rgba(15,118,110,.15), transparent 32%),
        radial-gradient(circle at 88% 18%, rgba(249,115,22,.15), transparent 28%),
        radial-gradient(circle at 50% 86%, rgba(20,184,166,.12), transparent 30%),
        #fbfaf7;
    }
    .hero::after {
      content: "";
      position: absolute;
      inset: 0;
      z-index: -1;
      opacity: .35;
      background-image:
        linear-gradient(rgba(31,41,51,.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(31,41,51,.045) 1px, transparent 1px);
      background-size: 42px 42px;
    }
    .center { text-align: center; }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 15px;
      border-radius: 999px;
      border: 1px solid #b7ded8;
      background: rgba(230, 244, 241, .9);
      color: var(--brand-dark);
      font-size: 14px;
      font-weight: 700;
      box-shadow: 0 10px 24px rgba(15, 118, 110, .08);
    }
    h1 {
      max-width: 880px;
      margin: 30px auto 22px;
      font-size: clamp(48px, 8vw, 84px);
      line-height: 1.05;
      letter-spacing: 0;
    }
    .gradient-text {
      color: transparent;
      background: linear-gradient(90deg, #0f766e, #14b8a6, #f97316);
      -webkit-background-clip: text;
      background-clip: text;
    }
    .hero p {
      max-width: 720px;
      margin: 0 auto;
      color: var(--muted);
      font-size: 20px;
    }
    .hero-actions {
      display: flex;
      justify-content: center;
      gap: 14px;
      margin: 36px 0 72px;
      flex-wrap: wrap;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      max-width: 720px;
      margin: 0 auto;
    }
    .glass {
      min-height: 122px;
      padding: 20px;
      border: 1px solid rgba(222, 216, 205, .9);
      border-radius: 18px;
      background: rgba(255, 255, 255, .72);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
      display: grid;
      place-items: center;
      gap: 5px;
    }
    .glass svg { color: var(--brand); }
    .glass strong { color: var(--brand-dark); font-size: 14px; }
    .glass span { color: #8a8278; font-size: 13px; }
    section { padding: 112px 0; }
    .soft { background: var(--panel); }
    .section-head {
      text-align: center;
      max-width: 760px;
      margin: 0 auto 58px;
    }
    .kicker {
      display: inline-flex;
      padding: 6px 15px;
      border-radius: 999px;
      background: var(--brand-soft);
      color: var(--brand-dark);
      font-size: 14px;
      font-weight: 800;
      margin-bottom: 18px;
    }
    h2 {
      margin: 0 0 15px;
      font-size: clamp(34px, 5vw, 52px);
      line-height: 1.08;
      letter-spacing: 0;
    }
    .section-head p {
      margin: 0 auto;
      color: var(--muted);
      font-size: 18px;
      max-width: 680px;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 22px;
    }
    .card {
      padding: 26px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--surface);
      box-shadow: 0 14px 34px rgba(15, 23, 42, 0.04);
      transition: transform .18s ease, box-shadow .18s ease;
    }
    .card:hover {
      transform: translateY(-3px);
      box-shadow: var(--shadow);
    }
    .icon {
      width: 46px;
      height: 46px;
      border-radius: 14px;
      display: grid;
      place-items: center;
      margin-bottom: 18px;
      border: 1px solid currentColor;
      background: color-mix(in srgb, currentColor 10%, white);
    }
    .card-title {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 11px;
    }
    .card h3 {
      margin: 0;
      font-size: 19px;
      line-height: 1.25;
    }
    .chip {
      flex: none;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #f8f6f2;
      color: #706a61;
      padding: 3px 10px;
      font-size: 12px;
      font-weight: 700;
    }
    .card p {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }
    .timeline {
      position: relative;
      max-width: 820px;
      margin: 0 auto;
      display: grid;
      gap: 22px;
    }
    .timeline::before {
      content: "";
      position: absolute;
      left: 20px;
      top: 36px;
      bottom: 36px;
      width: 1px;
      background: linear-gradient(#f97316, #0f766e, #14b8a6, #7c3aed);
    }
    .step {
      display: grid;
      grid-template-columns: 40px 1fr;
      gap: 20px;
      align-items: start;
      position: relative;
    }
    .num {
      width: 40px;
      height: 40px;
      border-radius: 13px;
      background: var(--step);
      color: white;
      display: grid;
      place-items: center;
      font-size: 14px;
      font-weight: 850;
      box-shadow: 0 14px 26px color-mix(in srgb, var(--step) 24%, transparent);
      z-index: 1;
    }
    .step .card { padding: 20px; }
    .step h3 { margin: 0 0 5px; font-size: 18px; }
    .agent-panel {
      max-width: 900px;
      margin: 0 auto;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: white;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .mode-row {
      display: flex;
      gap: 8px;
      padding: 18px 18px 0;
      flex-wrap: wrap;
    }
    .mode {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fff;
      color: #475569;
      padding: 8px 13px;
      font-weight: 750;
      font-size: 14px;
    }
    .mode.active {
      background: var(--brand-soft);
      border-color: #9fd7cf;
      color: var(--brand-dark);
    }
    .agent-body { padding: 18px; }
    textarea {
      width: 100%;
      min-height: 150px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      color: var(--ink);
      font: inherit;
      font-size: 16px;
      outline: none;
      background: #fff;
    }
    textarea:focus {
      border-color: #8dd4ca;
      box-shadow: 0 0 0 4px rgba(15, 118, 110, .1);
    }
    .run-row {
      margin-top: 12px;
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: center;
      flex-wrap: wrap;
    }
    .hint { color: #94a3b8; font-size: 14px; }
    .examples {
      border-top: 1px solid var(--line);
      padding: 18px;
      background: #f8f6f2;
    }
    .examples h3 {
      margin: 0 0 12px;
      font-size: 14px;
      color: #475569;
    }
    .example-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .example {
      text-align: left;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      padding: 12px 14px;
      color: #334155;
      font: inherit;
      cursor: pointer;
    }
    .example span {
      display: block;
      color: var(--brand-dark);
      font-size: 12px;
      font-weight: 800;
      margin-bottom: 3px;
    }
    .result {
      display: none;
      border-top: 1px solid var(--line);
      padding: 18px;
    }
    .result.show { display: block; }
    .result strong { display: block; margin-bottom: 10px; }
    .links { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
    .links a {
      display: inline-flex;
      min-height: 34px;
      align-items: center;
      padding: 0 12px;
      border-radius: 999px;
      background: var(--brand-soft);
      color: var(--brand-dark);
      font-size: 14px;
      font-weight: 750;
    }
    pre {
      max-height: 300px;
      overflow: auto;
      margin: 0;
      padding: 15px;
      border-radius: 14px;
      background: #17211f;
      color: #dcf7f2;
      font-size: 12px;
      white-space: pre-wrap;
    }
    .error { color: #dc2626; }
    footer {
      background: var(--footer);
      color: #94a3b8;
      padding: 54px 0 28px;
    }
    .footer-grid {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: 40px;
      margin-bottom: 34px;
    }
    footer .brand { color: white; margin-bottom: 14px; }
    footer p, footer li { color: #94a3b8; font-size: 14px; }
    footer ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 9px; }
    footer h4 { margin: 0 0 14px; color: white; }
    .footbar {
      border-top: 1px solid #1e293b;
      padding-top: 22px;
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      font-size: 12px;
      color: #64748b;
    }

    @media (max-width: 820px) {
      .nav-links { display: none; }
      .stats, .cards, .footer-grid, .example-grid { grid-template-columns: 1fr; }
      .hero { min-height: auto; }
      h1 { font-size: clamp(42px, 13vw, 64px); }
      .hero p { font-size: 18px; }
    }
    @media (max-width: 560px) {
      .nav-inner, .wrap { width: min(100% - 28px, 1120px); }
      .nav .btn { display: none; }
      section { padding: 82px 0; }
      .timeline::before { display: none; }
      .step { grid-template-columns: 1fr; gap: 12px; }
    }
  </style>
</head>
<body>
  <nav class="nav">
    <div class="nav-inner">
      <a href="#" class="brand">
        <span class="mark" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" stroke-width="2"/><rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" stroke-width="2"/><path d="M15 2v2M15 20v2M9 2v2M9 20v2M2 9h2M2 15h2M20 9h2M20 15h2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </span>
        <span>Research<span>Agent</span></span>
      </a>
      <div class="nav-links">
        <a href="#services">Services</a>
        <a href="#how-it-works">How It Works</a>
        <a href="#agent">Try Agent</a>
      </div>
      <a href="#agent" class="btn">Try Free -></a>
    </div>
  </nav>

  <main>
    <section class="hero">
      <div class="wrap center">
        <div class="badge">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M12 2l1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>
          Groq + Tavily research workspace
        </div>
        <h1>Turn any topic into a<br><span class="gradient-text">cited research brief.</span></h1>
        <p>A focused interface for your Python agent: plan the research, collect live sources, filter weak evidence, extract findings, and export a report without leaving the browser.</p>
        <div class="hero-actions">
          <a href="#agent" class="btn">Start for Free
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M5 12h14m-7-7 7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </a>
          <a href="#how-it-works" class="btn secondary">See How It Works</a>
        </div>
        <div class="stats">
          <div class="glass">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M2 12h20M12 2a14.5 14.5 0 0 1 0 20M12 2a14.5 14.5 0 0 0 0 20" stroke="currentColor" stroke-width="2"/></svg>
            <strong>Live Discovery</strong><span>Tavily web results</span>
          </div>
          <div class="glass">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M3 3v18h18M8 17v-4M13 17V7M18 17v-8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            <strong>Evidence Pipeline</strong><span>Plan, score, summarize</span>
          </div>
          <div class="glass">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" stroke="currentColor" stroke-width="2"/><path d="M14 2v6h6M8 13h8M8 17h5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            <strong>Export Ready</strong><span>HTML, Markdown, JSON</span>
          </div>
        </div>
      </div>
    </section>

    <section id="services" class="soft">
      <div class="wrap">
        <div class="section-head">
          <span class="kicker">Agent Capabilities</span>
          <h2>The same representation, designed for your agent.</h2>
          <p>The page explains the complete research loop clearly while keeping a different light visual style from the reference project.</p>
        </div>
        <div class="cards">
          <article class="card" style="color:#d97706"><div class="icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 5a3 3 0 0 0-6 .1 4 4 0 0 0-1.7 6.2A4 4 0 0 0 12 18V5ZM12 5a3 3 0 0 1 6 .1 4 4 0 0 1 1.7 6.2A4 4 0 0 1 12 18V5Z" stroke="currentColor" stroke-width="2"/></svg></div><div class="card-title"><h3>Planning Agent</h3><span class="chip">Groq</span></div><p>Breaks a broad topic into focused sub-questions and a report outline.</p></article>
          <article class="card" style="color:#0891b2"><div class="icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="2"/><path d="m21 21-4.3-4.3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div><div class="card-title"><h3>Research Agent</h3><span class="chip">Tavily</span></div><p>Searches the live web and retrieves source snippets for every sub-question.</p></article>
          <article class="card" style="color:#7c3aed"><div class="icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M4 14h6M4 10h10M4 6h16M4 18h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div><div class="card-title"><h3>Source Scoring</h3><span class="chip">Filter</span></div><p>Scores sources for relevance and keeps stronger evidence for synthesis.</p></article>
          <article class="card" style="color:#059669"><div class="icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="m12 3 9 5-9 5-9-5 9-5Z" stroke="currentColor" stroke-width="2"/><path d="m3 13 9 5 9-5" stroke="currentColor" stroke-width="2"/></svg></div><div class="card-title"><h3>Structured Memory</h3><span class="chip">JSON</span></div><p>Saves extracted claims, citations, quotes, and findings for later use.</p></article>
          <article class="card" style="color:#e11d48"><div class="icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M6 3v12M18 9a6 6 0 0 1-6 6H6" stroke="currentColor" stroke-width="2"/><circle cx="18" cy="6" r="3" stroke="currentColor" stroke-width="2"/><circle cx="6" cy="18" r="3" stroke="currentColor" stroke-width="2"/></svg></div><div class="card-title"><h3>Gap Loops</h3><span class="chip">Agentic</span></div><p>Refines the query and searches again when coverage is too thin.</p></article>
          <article class="card" style="color:#0f766e"><div class="icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M13 2 3 14h8l-1 8 11-13h-8l1-7Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg></div><div class="card-title"><h3>Report Delivery</h3><span class="chip">Files</span></div><p>Generates Markdown, HTML, and raw findings files in the output folder.</p></article>
        </div>
      </div>
    </section>

    <section id="how-it-works">
      <div class="wrap">
        <div class="section-head">
          <span class="kicker" style="background:#fff3e8;color:#c2410c">Workflow</span>
          <h2>From rough idea to final report</h2>
          <p>The representation stays familiar: describe the goal, let the agent work through each stage, then open the finished outputs.</p>
        </div>
        <div class="timeline">
          <div class="step" style="--step:#f97316"><div class="num">01</div><div class="card"><h3>Enter the research prompt</h3><p>Start with a topic, question, market, technology, or decision you want investigated.</p></div></div>
          <div class="step" style="--step:#0f766e"><div class="num">02</div><div class="card"><h3>Break it into sub-questions</h3><p>Groq creates a structured plan and a report outline before sources are gathered.</p></div></div>
          <div class="step" style="--step:#14b8a6"><div class="num">03</div><div class="card"><h3>Search and filter evidence</h3><p>Tavily retrieves sources; the agent scores, keeps, and summarizes the useful ones.</p></div></div>
          <div class="step" style="--step:#eab308"><div class="num">04</div><div class="card"><h3>Fill gaps with another pass</h3><p>If the evidence is too thin, the agent refines the query and searches again.</p></div></div>
          <div class="step" style="--step:#7c3aed"><div class="num">05</div><div class="card"><h3>Publish the report files</h3><p>The final output is saved as Markdown, HTML, and raw findings JSON.</p></div></div>
        </div>
      </div>
    </section>

    <section id="agent" class="soft">
      <div class="wrap">
        <div class="section-head">
          <span class="kicker">Live Agent</span>
          <h2>Run your agent from the browser</h2>
          <p>Use the same backend you already had, now with a clean light control panel.</p>
        </div>
        <div class="agent-panel">
          <div class="mode-row">
            <button class="mode active" type="button">Research Run</button>
            <button class="mode" type="button">Cited Output</button>
            <button class="mode" type="button">Source Trace</button>
          </div>
          <form id="run-form" class="agent-body">
            <textarea id="topic" name="topic" placeholder="Example: Analyse AI engineer skills needed for freshers in 2026" required></textarea>
            <div class="run-row">
              <span class="hint">Runs locally with Groq LLaMA 3.3 70B + Tavily Search</span>
              <button id="run-button" class="btn" type="submit">Run
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M5 12h14m-7-7 7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </button>
            </div>
          </form>
          <div class="examples">
            <h3>Try an example</h3>
            <div class="example-grid">
              <button class="example" type="button"><span>Research Only</span>Analyse AI engineer skills needed for freshers in 2026</button>
              <button class="example" type="button"><span>Market Research</span>Future of nuclear energy in India</button>
              <button class="example" type="button"><span>Technology</span>Best practices for RAG pipelines in production AI systems</button>
              <button class="example" type="button"><span>Healthcare</span>Impact of AI on healthcare delivery and patient outcomes</button>
            </div>
          </div>
          <div id="result" class="result" aria-live="polite"></div>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <div class="wrap">
      <div class="footer-grid">
        <div>
          <div class="brand"><span class="mark" aria-hidden="true"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" stroke-width="2"/><rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" stroke-width="2"/></svg></span><span>Research<span>Agent</span></span></div>
          <p>Autonomous research workspace for turning topics into cited, exportable reports.</p>
        </div>
        <div><h4>Tech Stack</h4><ul><li>Groq LLaMA 3.3</li><li>Tavily Search</li><li>Python</li><li>Markdown + HTML</li></ul></div>
        <div><h4>Links</h4><ul><li><a href="#agent">Try Agent</a></li><li><a href="#services">Services</a></li><li><a href="#how-it-works">How It Works</a></li></ul></div>
      </div>
      <div class="footbar"><span>Built with Groq + Tavily</span><span>ResearchAgent 2026</span></div>
    </div>
  </footer>

  <script>
    const form = document.querySelector("#run-form");
    const topic = document.querySelector("#topic");
    const button = document.querySelector("#run-button");
    const result = document.querySelector("#result");

    document.querySelectorAll(".example").forEach((example) => {
      example.addEventListener("click", () => {
        topic.value = example.textContent.replace(/Research Only|Market Research|Technology|Healthcare/g, "").trim();
        topic.focus();
      });
    });

    const escapeHtml = (value) => value.replace(/[&<>]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[ch]));

    function renderRunning() {
      result.className = "result show";
      result.innerHTML = "<strong>Agent is running...</strong><p class=\"hint\">This can take a minute or two while the agent searches, scores sources, summarizes findings, and writes the report.</p>";
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
        button.innerHTML = 'Run <svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M5 12h14m-7-7 7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
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
