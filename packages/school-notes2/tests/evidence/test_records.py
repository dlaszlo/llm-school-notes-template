import hashlib

import pytest

from school_notes2.evidence import records

PAGES = [{"seq": 1, "package": "Óra 1", "file": "füzet.pdf", "page": 2,
          "path": "sources/gazdasag/ora-1/p0001.jpg", "sha256": "0" * 64, "duplicate_of": None}]


def setup(tmp_path):
    img = tmp_path / "sources/gazdasag/ora-1/p0001.jpg"
    img.parent.mkdir(parents=True)
    img.write_bytes(b"jpeg-bytes")
    fig = tmp_path / "wiki/assets/abra.svg"
    fig.parent.mkdir(parents=True)
    fig.write_bytes(b"<svg/>")
    return hashlib.sha256(b"jpeg-bytes").hexdigest()


def test_record_path():
    assert str(records.record_path("wiki/gazdasag/szukosseg.md")) == \
        "docs/evidence/pages/gazdasag/szukosseg.md"
    with pytest.raises(records.RecordError):
        records.record_path("docs/x.md")


def test_writer_checks_resolve_seq_and_are_idempotent(tmp_path):
    digest = setup(tmp_path)
    checks = [{"page": "wiki/gazdasag/szukosseg.md", "image": 1, "locator": "2. feladat",
               "observed": "A táblázat három sora.", "decision": "changed", "note": "pótolva"},
              {"page": "wiki/gazdasag/szukosseg.md", "image": "wiki/assets/abra.svg",
               "locator": "ábra", "observed": "Nyíl balra.", "decision": "confirmed"}]
    kw = dict(run_id="run-1", checker="astra/high", at="2026-10-03T10:00:00+02:00",
              fetch_pages=PAGES)
    written = records.append(tmp_path, records.from_writer(checks), **kw)
    assert written == ["docs/evidence/pages/gazdasag/szukosseg.md"]
    text = (tmp_path / written[0]).read_text(encoding="utf-8")
    assert text.startswith("# Bizonyítékrekord: wiki/gazdasag/szukosseg.md\n\n## 2026-10-03")
    assert f"`sources/gazdasag/ora-1/p0001.jpg` (sha256 `{digest}`)" in text
    assert "Forrás: Óra 1 / füzet.pdf, 2. oldal" in text and "Megjegyzés: pótolva" in text
    assert records.append(tmp_path, records.from_writer(checks), **kw) == []
    records.append(tmp_path, records.from_writer(checks[:1]), **{**kw, "run_id": "run-2"})
    assert (tmp_path / written[0]).read_text(encoding="utf-8").startswith(text)


def test_reviewer_figures(tmp_path):
    setup(tmp_path)
    figs = [{"file": "wiki/assets/abra.svg", "page": "wiki/gazdasag/x.md", "verdict": "hibás",
             "checks": {"felirat": False}, "observed": "A felirat hiányzik."}]
    written = records.append(tmp_path, records.from_reviewer(figs), run_id="review-1",
                             checker="opus-5.5/high", at="2026-10-04T03:20:00+02:00")
    text = (tmp_path / written[0]).read_text(encoding="utf-8")
    assert "Döntés: hibás" in text and '{"felirat": false}' in text


@pytest.mark.parametrize("image", ["../outside.jpg", "/etc/passwd", "wiki/assets/nincs.png", 7])
def test_bad_images_are_refused(tmp_path, image):
    setup(tmp_path)
    entry = records.Entry("wiki/a/b.md", image, "x", "y", "confirmed")
    with pytest.raises(records.RecordError):
        records.append(tmp_path, [entry], run_id="r", checker="c", at="t", fetch_pages=PAGES)
