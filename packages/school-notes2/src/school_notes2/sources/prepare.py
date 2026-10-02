"""Uniform source images (plan 4.2): photos and PDF pages become ≤ max_side JPEGs."""

import re
import subprocess
from pathlib import Path

from .toolload import load_tool


def prepare_image(src: Path, dst: Path, max_side_px: int, quality: int,
                  tools_dir: Path | None = None) -> str:
    """tools/prepare_photo.prepare: upright, downscaled only, no metadata; returns the SHA-256."""
    _, digest = load_tool("prepare_photo", tools_dir).prepare(src, dst, max_side_px, quality)
    return digest


def pdf_page_count(pdf: Path, timeout_s: float = 120) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, timeout=timeout_s,
                         check=True).stdout
    match = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not match:
        raise ValueError(f"pdfinfo gave no page count for {pdf.name}")
    return int(match.group(1))


def pdf_pages(pdf: Path, out_dir: Path, dpi: int, timeout_s: float = 900) -> list[Path]:
    """Render every page to PNG (`pdftoppm -r <dpi> -png`); one lossy step follows later."""
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(out_dir / "page")],
                   capture_output=True, timeout=timeout_s, check=True)
    pages = sorted(out_dir.glob("page-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
    if len(pages) != pdf_page_count(pdf):
        raise ValueError(f"pdftoppm rendered {len(pages)} pages of {pdf.name}")
    return pages
