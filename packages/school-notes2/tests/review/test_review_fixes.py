import json

from school_notes2.review import nightly
from school_notes2.state import phase


def test_invalid_figures_are_dropped_not_fatal(tmp_path):
    task = phase.create(tmp_path, "benedek", "review", "cron", "reviewing")
    (task.dir / "in").mkdir()
    (task.dir / "in/images.json").write_text(json.dumps(
        [{"path": "wiki/assets/abra.svg", "kind": "figure", "file": "images/001-abra.png"}]))
    work = tmp_path / "wt"
    (work / "wiki/m").mkdir(parents=True)
    (work / "wiki/m/a.md").write_text("# a\n")
    good = {"file": "images/001-abra.png", "page": "wiki/m/a.md", "verdict": "ok", "observed": "o"}
    bad = {"file": "images/999.png", "page": "wiki/m/nincs", "verdict": "ok", "observed": "o"}
    nightly.record_review(task, {"verdict": "ok", "findings": [], "figures": [good, bad]}, work)
    saved = json.loads((task.dir / "review.json").read_text())
    assert saved["figures"] == [{**good, "file": "wiki/assets/abra.svg"}]
    assert task.get("dropped_figures") == [{"file": "images/999.png", "page": "wiki/m/nincs"}]
