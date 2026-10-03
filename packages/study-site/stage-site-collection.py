#!/usr/bin/env python3
"""Stage verified site bundles under their existing base paths; never deploy.

Access control is an external prerequisite, not supplied by robots or headers.
Only Python's standard library and this Git checkout's verifier are used.
"""
import argparse
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

SPEC = importlib.util.spec_from_file_location("release_bundle", Path(__file__).with_name("release-bundle.py"))
BUNDLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUNDLE)
MAX_FILES = 20_000
MAX_FILE_BYTES = 25 * 1024 * 1024
HEADERS = """/*
  Cache-Control: private, no-store
  X-Robots-Tag: noindex, nofollow, noarchive
  X-Content-Type-Options: nosniff
  Referrer-Policy: same-origin
"""


def write_shell(site, title, content):
    site.mkdir()
    (site / "index.html").write_text(
        '<!doctype html><html lang="hu"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        f'<title>{html.escape(title)}</title><main><h1>{html.escape(title)}</h1>'
        f'{content}</main></html>\n', encoding="utf-8")
    (site / "404.html").write_text(
        '<!doctype html><html lang="hu"><meta charset="utf-8">'
        '<title>Nem található</title><h1>Ez az oldal nem található.</h1></html>\n', encoding="utf-8")
    (site / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    (site / "_headers").write_text(HEADERS, encoding="utf-8")


def stage(output, entries=(), bootstrap=False):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Output already exists; use a new staging directory")
    if bootstrap == bool(entries):
        raise ValueError("Choose either an empty bootstrap or reviewed bundles")
    bases = []
    for archive, base, tag, title in entries:
        if not re.fullmatch(r"/[a-z0-9][a-z0-9-]*/", base) or base in bases:
            raise ValueError("Each base must be a unique single lowercase URL segment")
        bases.append(base)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".site-stage-") as temp:
        work = Path(temp)
        result = work / "result"
        result.mkdir()
        site = result / "site"
        if bootstrap:
            content = '<p>Belépésvédelem ellenőrzése. Ez a próbaoldal nem tartalmaz tananyagot.</p>'
        else:
            content = '<ul>' + ''.join(
                f'<li><a href="{base}">{html.escape(title)}</a></li>'
                for _, base, _, title in entries) + '</ul>'
        write_shell(site, "Tanulási jegyzetek", content)
        sources = []
        for index, (archive, base, tag, title) in enumerate(entries):
            extracted = work / f"verified-{index}"
            BUNDLE.verify(archive, extracted, base, tag)
            shutil.move(str(extracted), site / base.strip("/"))
            sources.append({"base": base, "release": tag,
                            "archive_sha256": hashlib.sha256(Path(archive).read_bytes()).hexdigest()})
        files = sorted(p for p in site.rglob("*") if p.is_file())
        if len(files) > MAX_FILES or any(p.stat().st_size > MAX_FILE_BYTES for p in files):
            raise ValueError("Cloudflare Pages file count or individual asset size exceeded")
        record = {"schema": 1, "kind": "bootstrap" if bootstrap else "reviewed-site-collection",
                  "access_control": "NOT PROVIDED: verify Cloudflare Access before uploading content",
                  "sources": sources, "files": {
                      p.relative_to(site).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in files}, "bytes": sum(p.stat().st_size for p in files)}
        # Private deployment evidence stays outside the served directory.
        (result / "staging-receipt.private.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result.rename(output)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    parser.add_argument("--bootstrap", action="store_true", help="Empty, non-sensitive access-control test site")
    parser.add_argument("--bundle", nargs=4, action="append", default=[], metavar=("ARCHIVE", "BASE", "TAG", "TITLE"))
    args = parser.parse_args()
    receipt = stage(args.output, args.bundle, args.bootstrap)
    print(json.dumps({"kind": receipt["kind"], "files": len(receipt["files"]), "bytes": receipt["bytes"], "deployed": False}))
