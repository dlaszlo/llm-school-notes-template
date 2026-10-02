"""Stand-in for check-browser.mjs: OVERFLOW in a page's HTML is an error on that page."""
import json
import sys
from pathlib import Path

origin, payload_path, _browser, report_path, _query, *rest = sys.argv[1:]
payload = json.loads(Path(payload_path).read_text())
only = set(json.loads(Path(rest[0]).read_text())) if rest else None
site = Path(payload_path).parent / "site"
report = {"origin": origin, "pages": [], "errors": []}
for page in payload["pages"]:
    if only is not None and page["path"] not in only:
        continue
    report["pages"].append(page["path"])
    if "OVERFLOW" in (site / page["route"] / "index.html").read_text():
        report["errors"].append({"url": page["url"], "path": page["path"], "overflow": True, "width": 320})
Path(report_path).write_text(json.dumps(report))
sys.exit(1 if report["errors"] else 0)
