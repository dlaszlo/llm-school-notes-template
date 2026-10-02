#!/usr/bin/env python3
"""Store an incoming photo in sources/: same resolution, smaller file, no metadata.

Usage: python3 tools/prepare_photo.py [--max-side PX] [--quality Q] <incoming image> <target path in sources/>

* The image is turned upright (the phone's EXIF orientation is applied to the pixels).
* By default it is saved at the SAME resolution as JPEG quality 90 (PNG input to a .png
  target stays lossless PNG). With --max-side the longer side is reduced to at most PX
  pixels; a smaller image is never enlarged. The School Notes v2 tool uses 2000 px and
  quality 85 (plan 4.2) through the importable `prepare()` function.
* ALL metadata is dropped: EXIF (GPS position, device, date), XMP, ICC profile,
  comments. Only the pixels are kept.

The saved file is the source: it is what gets read at ingest, what the
nightly review checks against, and what content_sha256 records. The script
prints that hash. It never overwrites an existing file.
"""
import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageOps

try:  # HEIC/HEIF from iPhones, if the optional plugin is installed
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

QUALITY = 90


def prepare(src, dst, max_side_px=None, quality=QUALITY):
    """Store `src` as `dst` (upright, optionally downscaled, no metadata); return (size, sha256).

    Deterministic for a fixed Pillow version, so the same input always gives the same hash.
    """
    src, dst = Path(src), Path(dst)
    if dst.exists():
        raise FileExistsError(f"{dst} already exists - sources are never overwritten")
    im = ImageOps.exif_transpose(Image.open(src))
    if max_side_px and max(im.size) > max_side_px:
        # thumbnail() only ever shrinks and keeps the aspect ratio.
        im.thumbnail((max_side_px, max_side_px), Image.Resampling.LANCZOS)
    # A fresh image holds only pixels: no EXIF, XMP, ICC, or comments carry over.
    if dst.suffix.lower() == ".png":
        mode = "RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB"
        clean = Image.frombytes(mode, im.size, im.convert(mode).tobytes())
        dst.parent.mkdir(parents=True, exist_ok=True)
        clean.save(dst, optimize=True)
    else:
        if dst.suffix.lower() not in (".jpg", ".jpeg"):
            raise ValueError("target must end in .jpg, .jpeg or .png")
        clean = Image.frombytes("RGB", im.size, im.convert("RGB").tobytes())
        dst.parent.mkdir(parents=True, exist_ok=True)
        clean.save(dst, quality=quality, optimize=True)
    return im.size, hashlib.sha256(dst.read_bytes()).hexdigest()


def main():
    args = sys.argv[1:]
    options = {}
    while args and args[0] in ("--max-side", "--quality") and len(args) > 1:
        options[args[0]] = int(args[1])
        args = args[2:]
    if len(args) != 2:
        sys.exit(__doc__)
    src, dst = Path(args[0]), Path(args[1])
    try:
        size, digest = prepare(src, dst, options.get("--max-side"), options.get("--quality", QUALITY))
    except (FileExistsError, ValueError) as exc:
        sys.exit(str(exc))
    print(f"{dst}  {size[0]}x{size[1]}  {src.stat().st_size // 1024} KB -> {dst.stat().st_size // 1024} KB  sha256 {digest}")


if __name__ == "__main__":
    main()
