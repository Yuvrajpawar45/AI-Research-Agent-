"""
PDF Parser Tool — extracts text from local PDF files using PyMuPDF (fitz).
Optional: only needed if you want to research local PDF papers.
"""

import os


def parse_pdf(path: str, max_chars: int = 8000) -> dict:
    """
    Extract text from a PDF file.
    Returns {title, content, pages} or raises if fitz not installed.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF not installed. Run: pip install pymupdf\n"
            "Or skip PDF parsing — it's optional."
        )

    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF not found: {path}")

    doc = fitz.open(path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()

    full_text = "\n".join(text_parts)
    title = os.path.basename(path).replace(".pdf", "")

    return {
        "title":   title,
        "content": full_text[:max_chars],
        "pages":   len(text_parts),
        "url":     f"file://{os.path.abspath(path)}",
        "score":   0.8,   # assume local PDFs are relevant
    }


def parse_pdfs_in_folder(folder: str) -> list[dict]:
    """Parse all PDFs in a folder and return list of source dicts."""
    sources = []
    for fname in os.listdir(folder):
        if fname.lower().endswith(".pdf"):
            try:
                src = parse_pdf(os.path.join(folder, fname))
                sources.append(src)
                print(f"   📄 Parsed PDF: {fname} ({src['pages']} pages)")
            except Exception as e:
                print(f"   ⚠️  Could not parse {fname}: {e}")
    return sources
