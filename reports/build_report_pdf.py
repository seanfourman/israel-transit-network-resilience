"""Build the formal Hebrew final report PDF.

Takes reports/final_report_he.html (which references figures via {{FIG:relpath}}
tokens), inlines each figure as a base64 data URI so the document is fully
self-contained, then renders it to reports/final_report_he.pdf using headless
Edge/Chromium with page numbers.

Run:  python reports/build_report_pdf.py
"""
from __future__ import annotations

import base64
import mimetypes
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTML_SRC = REPO / "reports" / "final_report_he.html"
HTML_RENDER = REPO / "reports" / "_final_report_he.rendered.html"
PDF_OUT = REPO / "reports" / "final_report_he.pdf"
FIG_ROOT = REPO / "outputs" / "nb"

TOKEN = re.compile(r"\{\{FIG:([^}]+)\}\}")


def inline_figures(html: str) -> str:
    """Replace every {{FIG:relpath}} token with an <img> carrying a base64 data URI."""
    missing: list[str] = []

    def repl(match: re.Match) -> str:
        rel = match.group(1).strip()
        path = FIG_ROOT / rel
        if not path.exists():
            missing.append(rel)
            return f"<!-- MISSING FIGURE {rel} -->"
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'<img alt="{rel}" src="data:{mime};base64,{data}">'

    out = TOKEN.sub(repl, html)
    if missing:
        raise SystemExit("Missing figures:\n  " + "\n  ".join(missing))
    remaining = TOKEN.findall(out)
    if remaining:
        raise SystemExit(f"Unresolved figure tokens remain: {remaining}")
    return out


def find_edge() -> str | None:
    for c in (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if Path(c).exists():
            return c
    return None


def render_playwright(html_path: Path, pdf_path: Path) -> bool:
    """Preferred renderer: Playwright driving installed Edge, with footer page numbers."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    footer = (
        '<div style="width:100%;font-family:Arial;font-size:8px;color:#8a97a4;'
        'text-align:center;padding-top:2mm;">'
        '<span class="pageNumber"></span> / <span class="totalPages"></span></div>'
    )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge")
            page = browser.new_page()
            page.goto(html_path.as_uri(), wait_until="networkidle")
            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template="<div></div>",
                footer_template=footer,
                margin={"top": "18mm", "bottom": "16mm", "left": "18mm", "right": "18mm"},
            )
            browser.close()
        return True
    except Exception as e:  # pragma: no cover
        print("  playwright render failed:", str(e)[:200])
        return False


def render_edge_cli(edge: str, html_path: Path, pdf_path: Path) -> bool:
    """Fallback: Edge headless CLI (no page numbers, but reliable)."""
    cmd = [
        edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}", html_path.as_uri(),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return pdf_path.exists()


def main() -> None:
    html = HTML_SRC.read_text(encoding="utf-8")
    n_figs = len(TOKEN.findall(html))
    print(f"inlining {n_figs} figures ...")
    HTML_RENDER.write_text(inline_figures(html), encoding="utf-8")
    print(f"  wrote {HTML_RENDER.name} ({HTML_RENDER.stat().st_size/1024/1024:.1f} MB)")

    print("rendering PDF ...")
    if render_playwright(HTML_RENDER, PDF_OUT):
        print("  rendered via Playwright/Edge (with page numbers)")
    else:
        edge = find_edge()
        if not edge:
            raise SystemExit("No Chromium-based browser found for PDF rendering.")
        if render_edge_cli(edge, HTML_RENDER, PDF_OUT):
            print("  rendered via Edge CLI (no page numbers)")
        else:
            raise SystemExit("PDF rendering failed.")
    print(f"done -> {PDF_OUT}  ({PDF_OUT.stat().st_size/1024/1024:.2f} MB)")


if __name__ == "__main__":
    main()
