from school_notes2.state import phase


def test_reload_keeps_what_a_handler_saved_meanwhile(tmp_path):
    task = phase.create(tmp_path, "benedek", "notes", "cron", "writing")
    handler_copy = phase.load(task.dir)
    handler_copy.update(tool_writes={"docs/evidence/media/x/job.json": "ab" * 32})
    task.reload()
    task.update(writing_k=2)
    saved = phase.load(task.dir)
    assert saved.get("tool_writes") == {"docs/evidence/media/x/job.json": "ab" * 32}
    assert saved.get("writing_k") == 2
