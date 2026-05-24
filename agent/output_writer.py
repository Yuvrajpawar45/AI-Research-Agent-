"""
STEP 7 — Deliver Output
Saves the report as Markdown and optionally as HTML.
"""

import os
import json
from datetime import datetime
import config


def slugify(text: str) -> str:
    """Convert text to a safe filename."""
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in text)
    return safe.strip().replace(" ", "_")[:50]


def save_report(
    title: str,
    report_md: str,
    all_findings: dict,
) -> str:
    """Save the Markdown report and a JSON findings dump. Returns the report path."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{slugify(title)}_{timestamp}"

    # ── Save Markdown report ───────────────────────────────────
    md_path = os.path.join(config.OUTPUT_DIR, f"{base_name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n---\n\n")
        f.write(report_md)

    # ── Save JSON findings (for RAG / follow-up) ───────────────
    json_path = os.path.join(config.OUTPUT_DIR, f"{base_name}_findings.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "title": title,
                "generated_at": datetime.now().isoformat(),
                "findings": all_findings,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ── Save simple HTML version ───────────────────────────────
    try:
        import markdown as md_lib
        html_body = md_lib.markdown(report_md, extensions=["tables", "fenced_code"])
        html = HTML_TEMPLATE.format(title=title, body=html_body)
        html_path = os.path.join(config.OUTPUT_DIR, f"{base_name}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"   📄 HTML report: {html_path}")
    except ImportError:
        pass  # markdown package is optional

    print(f"   📝 Markdown report: {md_path}")
    print(f"   🗄️  Findings JSON:  {json_path}")
    return md_path


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 860px; margin: 40px auto;
          padding: 0 24px; color: #1a1a2e; line-height: 1.7; }}
  h1 {{ color: #0f3460; border-bottom: 3px solid #e94560; padding-bottom: 12px; }}
  h2 {{ color: #16213e; margin-top: 2em; }}
  a {{ color: #e94560; }}
  blockquote {{ border-left: 4px solid #e94560; padding-left: 16px;
                color: #555; font-style: italic; }}
  code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
</style>
</head>
<body>
<h1>{title}</h1>
{body}
</body>
</html>
"""
