import json

from school_notes2.wiki import check, public


def page(repo, body):
    path = repo / "wiki/proba/anim.md"
    path.write_text("---\ntype: topic\ntitle: A\ndescription: D.\nchapter: alapok\norder: 40\n---\n\n" + body,
                    encoding="utf-8")
    return "wiki/proba/anim.md"


def render(repo, folder="wiki/assets/anim"):
    d = repo / folder
    d.mkdir(parents=True)
    (d / "figure.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom")
    (d / "figure.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (repo / "wiki/proba/scene.pov").write_text("sphere{0,1}")
    import hashlib
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    (d / "render.json").write_text(json.dumps({
        "source": "wiki/proba/scene.pov", "source_sha256": h(repo / "wiki/proba/scene.pov"),
        "outputs": {"figure.mp4": {"sha256": h(d / "figure.mp4")}, "figure.png": {"sha256": h(d / "figure.png")}}}))


def test_rendered_animation_passes_and_becomes_two_assets(repo):
    render(repo)
    rel = page(repo, "![Mozgó gömb](../assets/anim/figure.mp4)\n")
    assert not [i for i in check.check_files(repo, [rel]) if "animation" in i["message"]]
    images, _ = public.linked_targets(repo, [rel])
    assert {"wiki/assets/anim/figure.mp4", "wiki/assets/anim/figure.png"} <= images
    rights = public.render_rights(repo)
    assert rights("wiki/assets/anim/figure.mp4")[0] == "authored"


def test_foreign_video_without_render_or_poster_is_refused(repo):
    d = repo / "wiki/assets/x"
    d.mkdir(parents=True)
    (d / "clip.mp4").write_bytes(b"x")
    rel = page(repo, "![Klip](../assets/x/clip.mp4)\n")
    messages = [i["message"] for i in check.check_files(repo, [rel])]
    assert any("poster" in m for m in messages) and any("not a tool render" in m for m in messages)
