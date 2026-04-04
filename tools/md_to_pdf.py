#!/usr/bin/env python3
"""
Convert Markdown study notes to PDF using fpdf2's HTML renderer.

Usage:
  uv run python tools/md_to_pdf.py path/to/file.md
  uv run python tools/md_to_pdf.py --all
  make pdf
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import markdown
    from fpdf import FPDF
except ImportError as e:
    print("Missing dependencies. From repo root run:", file=sys.stderr)
    print("  uv sync", file=sys.stderr)
    raise SystemExit(1) from e

ROOT = Path(__file__).resolve().parents[1]
UNICODE_FONT = "NotesUnicode"

MD_EXTENSIONS = ["fenced_code", "tables", "nl2br"]

def find_unicode_ttf() -> Path | None:
    """Prefer a TTF with wide Unicode coverage (platform-specific paths)."""
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/ARIALUNI.TTF"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def md_to_html(text: str) -> str:
    return markdown.markdown(text, extensions=MD_EXTENSIONS)


def strip_md_for_plain(text: str) -> str:
    """Fallback: crude plain text if HTML rendering fails."""
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```.*?```", "[code block]", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


class NotesPDF(FPDF):
    def __init__(self, body_font: str) -> None:
        super().__init__()
        self._body_font = body_font

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font(self._body_font, size=8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def prepare_pdf(body_font: str, unicode_ttf: Path | None) -> NotesPDF:
    """Create FPDF and register Unicode font on this instance when available."""
    pdf = NotesPDF(body_font=body_font)
    if unicode_ttf is not None:
        pdf.add_font(UNICODE_FONT, "", str(unicode_ttf))
    return pdf


def resolve_body_font(unicode_ttf: Path | None) -> str:
    return UNICODE_FONT if unicode_ttf is not None else "Helvetica"


def write_pdf(
    html: str,
    title: str,
    dest: Path,
    *,
    unicode_ttf: Path | None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    body_font = resolve_body_font(unicode_ttf)
    pdf = prepare_pdf(body_font, unicode_ttf)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_title(title)
    pdf.add_page()
    pdf.set_font(body_font, size=11)
    pdf.write_html(html, font_family=body_font)
    pdf.output(dest.as_posix())


def convert_file(md_path: Path, out_path: Path, *, unicode_ttf: Path | None) -> Path:
    raw = md_path.read_text(encoding="utf-8")
    html = md_to_html(raw)
    title = md_path.stem.replace("-", " ").replace("_", " ")
    body_font = resolve_body_font(unicode_ttf)

    try:
        write_pdf(html, title, out_path, unicode_ttf=unicode_ttf)
    except Exception:
        plain = strip_md_for_plain(raw)
        pdf = prepare_pdf(body_font, unicode_ttf)
        pdf.add_page()
        pdf.set_font(body_font, size=9)
        pdf.multi_cell(0, 5, plain)
        pdf.output(out_path.as_posix())
    return out_path


def collect_study_dirs() -> list[Path]:
    dirs: list[Path] = []
    topics = ROOT / "topics"
    if topics.is_dir():
        dirs.append(topics)
    for name in ("basic", "python-concurrency-interview"):
        p = ROOT / name
        if p.is_dir():
            dirs.append(p)
    return dirs


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown notes → PDF")
    parser.add_argument("paths", nargs="*", type=Path, help="Markdown files")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Convert all *.md under topics/ (if present), basic/, python-concurrency-interview/",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=ROOT / "media",
        help="Output directory (default: media/)",
    )
    args = parser.parse_args()
    out_dir = args.out_dir.resolve()
    unicode_ttf = find_unicode_ttf()

    targets: list[Path] = []
    if args.all:
        for d in collect_study_dirs():
            if d.is_dir():
                targets.extend(sorted(d.glob("*.md")))
    targets.extend(p.resolve() for p in args.paths)

    if not targets:
        parser.print_help()
        raise SystemExit(2)

    for p in targets:
        if not p.is_file():
            print(f"skip (not a file): {p}", file=sys.stderr)
            continue
        out = out_dir / f"{p.stem}.pdf"
        print(f"{p.name} -> {out}")
        convert_file(p, out, unicode_ttf=unicode_ttf)


if __name__ == "__main__":
    main()
