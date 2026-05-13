"""Build a DOCX copy of the Hebrew final report.

The Markdown file remains the source of truth. This script creates a simple
Word document with headings, tables, code blocks, and embedded figures.
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


REPORT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = REPORT_DIR.parent
SOURCE = REPORT_DIR / "final_report_he.md"
TARGET = REPORT_DIR / "final_report_he.docx"


def set_rtl(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph_format = paragraph._p.get_or_add_pPr()
    bidi = paragraph_format.find(qn("w:bidi"))
    if bidi is None:
        bidi = OxmlElement("w:bidi")
        paragraph_format.append(bidi)
    bidi.set(qn("w:val"), "1")


def set_run_font(run, size: int | None = None, bold: bool | None = None) -> None:
    run.font.name = "Arial"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def split_markdown_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def add_markdown_table(document: Document, lines: list[str]) -> None:
    rows = split_markdown_table(lines)
    if len(rows) >= 2 and all(set(cell.replace(":", "").replace("-", "")) == set() for cell in rows[1]):
        rows = [rows[0], *rows[2:]]
    if not rows:
        return

    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for row_idx, row in enumerate(rows):
        for col_idx, value in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            paragraph = cell.paragraphs[0]
            set_rtl(paragraph)
            run = paragraph.add_run(value)
            set_run_font(run, size=9, bold=row_idx == 0)


def add_code_block(document: Document, lines: list[str]) -> None:
    for line in lines:
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = paragraph.add_run(line)
        run.font.name = "Consolas"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        run.font.size = Pt(9)


def add_paragraph(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    set_rtl(paragraph)
    for part in re.split(r"(\*\*.*?\*\*)", text):
        if not part:
            continue
        bold = part.startswith("**") and part.endswith("**")
        value = part[2:-2] if bold else part
        run = paragraph.add_run(value)
        set_run_font(run, size=11, bold=bold)


def add_image(document: Document, alt: str, relative_path: str) -> None:
    image_path = (REPORT_DIR / relative_path).resolve()
    if not image_path.exists():
        add_paragraph(document, f"[תמונה חסרה: {relative_path}]")
        return
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Inches(5.8))
    caption = document.add_paragraph()
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_run = caption.add_run(alt)
    set_run_font(caption_run, size=9)
    caption_run.italic = True


def build_docx() -> None:
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)

    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    index = 0
    in_code = False
    code_lines: list[str] = []

    while index < len(lines):
        line = lines[index]

        if line.startswith("```"):
            if in_code:
                add_code_block(document, code_lines)
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue

        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if not line.strip():
            index += 1
            continue

        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            add_markdown_table(document, table_lines)
            continue

        image_match = re.match(r"!\[(.*?)\]\((.*?)\)", line)
        if image_match:
            add_image(document, image_match.group(1), image_match.group(2))
            index += 1
            continue

        if line.startswith("# "):
            paragraph = document.add_heading(line[2:].strip(), level=0)
            set_rtl(paragraph)
            index += 1
            continue

        if line.startswith("## "):
            paragraph = document.add_heading(line[3:].strip(), level=1)
            set_rtl(paragraph)
            index += 1
            continue

        if line.startswith("### "):
            paragraph = document.add_heading(line[4:].strip(), level=2)
            set_rtl(paragraph)
            index += 1
            continue

        add_paragraph(document, line)
        index += 1

    document.save(TARGET)
    print("reports/final_report_he.docx")


if __name__ == "__main__":
    build_docx()
