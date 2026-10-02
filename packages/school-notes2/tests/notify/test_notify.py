import stat

from school_notes2.notify import Mailer, Notice


def fake_msmtp(tmp_path, rc=0):
    script = tmp_path / "msmtp"
    out = tmp_path / "sent.eml"
    script.write_text(f"#!/bin/sh\ncat >> {out}\nexit {rc}\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script, out


def notice(kind="needs_owner:notes"):
    return Notice("benedek", kind, "20261003-0100-ab12", "finish", "needs_owner",
                  "content conflict while rebasing", "resolve in school-notes chat")


def test_one_mail_per_learner_and_kind_per_day(tmp_path, log):
    script, out = fake_msmtp(tmp_path)
    mailer = Mailer(tmp_path / "rc", "owner@example.com", tmp_path / "notify.json", log,
                    msmtp=str(script))
    assert mailer.send(notice())
    assert not mailer.send(notice())
    assert mailer.send(notice("prerequisite:login"))
    text = out.read_text()
    assert text.count("Subject:") == 2 and "school-notes status benedek" in text


def test_msmtp_failure_is_only_logged(tmp_path, log):
    script, _ = fake_msmtp(tmp_path, rc=75)
    mailer = Mailer(tmp_path / "rc", "owner@example.com", tmp_path / "notify.json", log,
                    msmtp=str(script))
    assert not mailer.send(notice())
    assert not (tmp_path / "notify.json").exists()
    assert '"notify.mail"' in log.main.read_text()
