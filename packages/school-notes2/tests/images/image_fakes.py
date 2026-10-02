"""Fixtures: a fake OpenRouter server, a shim that points learning_image.py at it, and a
worktree with one page holding an image marker. No real API, no real key."""

import base64
import io
import json
import threading
from datetime import date
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image

from school_notes2.images.settings import ImageSettings

TOOLS = Path(__file__).resolve().parents[4] / "tools"
KEY = "test-key-not-real"

PLAN = {"role": "banner", "language": "Hungarian", "goal": "Orient the learner.",
        "scope": "Economics, 9th grade.", "decision_reason": "Page needs a banner.",
        "context": "Termelési tényezők", "composition": "Wide low banner.",
        "visible_text": ["Termelési tényezők"],
        "claims": [{"text": "Illustrative scene only.", "source": "sources/gazdasag/p0001.jpg"}],
        "style": "Editorial illustration.", "aspect_ratio": "21:9", "constraints": "No extra text."}

PAGE = """---
type: topic
title: Termelési tényezők
---

<!-- image: termeles-banner -->

# Termelési tényezők

Szöveg.
"""


class FakeOpenRouter:
    """Answers queued actions: "ok", an HTTP status (int), or "drop" (no response)."""

    def __init__(self):
        self.actions: list = []
        self.requests: list[dict] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append({"auth": self.headers["Authorization"], "body": body})
                action = fake.actions.pop(0) if fake.actions else "ok"
                if action == "drop":
                    self.close_connection = True
                    self.connection.close()
                    return
                if action != "ok":
                    self.send_response(action)
                    self.end_headers()
                    self.wfile.write(b'{"error": "PRIVATE_PROVIDER_TEXT"}')
                    return
                data = json.dumps(_image_answer(len(fake.requests))).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/api/v1/images"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def calls(self) -> int:
        return len(self.requests)


def _image_answer(n: int) -> dict:
    out = io.BytesIO()
    Image.new("RGB", (420, 180), (200, 255 - n, 255)).save(out, format="PNG")
    return {"usage": {"cost": 0.04},
            "data": [{"b64_json": base64.b64encode(out.getvalue()).decode(), "media_type": "image/png"}]}


def write_shim(folder: Path, url: str) -> Path:
    shim = folder / "learning_image_shim.py"
    shim.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(TOOLS)!r})\n"
        "import learning_image as _m\n"
        "from learning_image import *  # noqa: F401,F403 - encoders for in-process use\n"
        f"_m.API = {url!r}\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(_m.main())\n")
    return shim


def make_worktree(root: Path, learner: str) -> Path:
    work = root / f"work-{learner}"
    (work / "wiki/gazdasag").mkdir(parents=True)
    (work / "sources/gazdasag").mkdir(parents=True)
    (work / "sources/gazdasag/p0001.jpg").write_bytes(b"photo")
    (work / "wiki/gazdasag/termeles.md").write_text(PAGE, encoding="utf-8")
    images = work / ".school-notes/images"
    images.mkdir(parents=True)
    (images / "termeles-banner.json").write_text(json.dumps(PLAN), encoding="utf-8")
    return work


def verdict(decision="accepted", **extra) -> dict:
    review = {"observed": "Cím és műhelyjelenet.", "decision": decision,
              "checks": {k: "pass" for k in ("sources", "context", "text", "visual_claims",
                                              "learning_goal", "phone", "a4")} | {"arrows": "not-applicable"},
              "material_defects": [] if decision == "accepted" else ["A cím hibás."],
              "description": "Termelési tényezők cím; pék és műhely.",
              "publication": {"observed": "A tömörített előnézet olvasható.", "checked": True}}
    review.update(extra)
    return review

