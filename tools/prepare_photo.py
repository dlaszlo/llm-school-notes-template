#!/usr/bin/env python3
"""Store an incoming photo in sources/: same resolution, smaller file, no metadata.

Usage: python3 tools/prepare_photo.py <incoming image> <target path in sources/>

* The image is turned upright (the phone's EXIF orientation is applied to the pixels).
* It is saved at the SAME resolution - nothing is scaled down - as JPEG quality 90
  (PNG input to a .png target stays lossless PNG). Visually identical at 100% zoom,
  about a quarter of a typical phone JPEG's size.
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


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    if dst.exists():
        sys.exit(f"{dst} already exists - sources are never overwritten")
    im = ImageOps.exif_transpose(Image.open(src))
    # A fresh image holds only pixels: no EXIF, XMP, ICC, or comments carry over.
    if dst.suffix.lower() == ".png":
        mode = "RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB"
        clean = Image.frombytes(mode, im.size, im.convert(mode).tobytes())
        dst.parent.mkdir(parents=True, exist_ok=True)
        clean.save(dst, optimize=True)
    else:
        if dst.suffix.lower() not in (".jpg", ".jpeg"):
            sys.exit("target must end in .jpg, .jpeg or .png")
        clean = Image.frombytes("RGB", im.size, im.convert("RGB").tobytes())
        dst.parent.mkdir(parents=True, exist_ok=True)
        clean.save(dst, quality=QUALITY, optimize=True)
    digest = hashlib.sha256(dst.read_bytes()).hexdigest()
    print(f"{dst}  {im.size[0]}x{im.size[1]}  {src.stat().st_size // 1024} KB -> {dst.stat().st_size // 1024} KB  sha256 {digest}")


if __name__ == "__main__":
    main()
