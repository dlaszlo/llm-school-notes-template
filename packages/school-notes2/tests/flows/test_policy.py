from school_notes2.flows import policy
from school_notes2.state import phase
from school_notes2.state.errors import BadWork, NeedsOwner, Prerequisite, Transient


class FakeMailer:
    def __init__(self):
        self.sent = []

    def send(self, notice):
        self.sent.append(notice)
        return True


def test_transient_stops_on_third_failed_invocation(tmp_path, log):
    task = phase.create(tmp_path, "benedek", "notes", "cron", "prepared")
    mailer = FakeMailer()
    for _ in range(2):
        policy.on_error(Transient("net"), task=task, student="benedek", step="fetch", log=log,
                        mailer=mailer)
    assert task.data["needs_owner"] is None and not mailer.sent
    policy.on_error(Transient("net"), task=task, student="benedek", step="fetch", log=log,
                    mailer=mailer)
    assert task.data["needs_owner"]["class"] == "transient" and len(mailer.sent) == 1


def test_success_in_the_second_hour_resets(tmp_path, log):
    task = phase.create(tmp_path, "benedek", "notes", "cron", "prepared")
    policy.on_error(Transient("net"), task=task, student="benedek", step="push", log=log,
                    mailer=None)
    policy.on_success(task)
    assert task.data["retries"] == 0


def test_bad_work_twice_needs_owner_but_not_interactive(tmp_path, log):
    task = phase.create(tmp_path, "barna", "notes", "interactive", "writing")
    policy.on_error(BadWork("x"), task=task, student="barna", step="writer", log=log,
                    mailer=None, interactive=True)
    assert task.data["llm_failures"] == 0
    for _ in range(2):
        policy.on_error(BadWork("x"), task=task, student="barna", step="writer", log=log,
                        mailer=None)
    assert task.data["needs_owner"]


def test_needs_owner_and_program_errors_stop_at_once(tmp_path, log):
    task = phase.create(tmp_path, "barna", "notes", "cron", "committed")
    mailer = FakeMailer()
    policy.on_error(NeedsOwner("conflict", todo="chat"), task=task, student="barna",
                    step="finish", log=log, mailer=mailer)
    assert task.data["needs_owner"]["todo"] == "chat"
    task2 = phase.create(tmp_path, "barna", "review", "cron", "prepared")
    policy.on_error(KeyError("boom"), task=task2, student="barna", step="nightly", log=log,
                    mailer=mailer)
    assert task2.data["needs_owner"]["class"] == "program"
    assert "traceback" in log.main.read_text()


def test_prerequisite_mails_without_touching_the_task(tmp_path, log):
    task = phase.create(tmp_path, "barna", "notes", "cron", "prepared")
    mailer = FakeMailer()
    policy.on_error(Prerequisite("login expired", todo="log in"), task=task, student="barna",
                    step="login", log=log, mailer=mailer)
    assert task.data["retries"] == 0 and mailer.sent[0].kind == "prerequisite:login"
