import json
import socket
import threading
import time

import pytest

from school_notes2.mcp.redact import redact
from school_notes2.mcp.server import Handlers, McpServer
from school_notes2.schemas import errors
from school_notes2.state.errors import NeedsOwner

CANARY = "CANARY-7f3e9a-SECRET-VALUE"


def handlers(**over):
    base = dict(check=lambda: {"problems": []},
                image_generate=lambda plan_id, note: {"plan_id": plan_id, "note": note},
                image_accept=lambda plan_id, review: {"accepted": plan_id},
                status=lambda: {"phase": "writing"},
                fetch=lambda: {"run_id": "new"}, finish=lambda: {"pushed": True},
                validate_review=lambda review: [] if "decision" in review else ["decision missing"])
    base.update(over)
    return Handlers(**base)


@pytest.fixture
def make(tmp_path, log):
    def factory(mode="interactive", wait_s=2.0, **over):
        return McpServer(student="benedek", mode=mode, handlers=handlers(**over), log=log,
                         jobs_dir=tmp_path / "jobs", run_id=lambda: "20261003-0100-ab12",
                         log_path="/srv/school-notes/logs/school-notes.log",
                         secrets=(CANARY,), wait_s=wait_s)
    return factory


def call(server, name, args=None):
    response = server.call_tool(name, args or {})
    assert not errors("mcp_response", response), errors("mcp_response", response)
    return response


def finish_job(server, response):
    job_id = response["result"]["job_id"]
    for _ in range(50):
        done = call(server, "wait", {"job_id": job_id})
        if not done["ok"] or done["result"]["state"] != "running":
            return done
    raise AssertionError("job did not finish")


def test_tools_list_depends_on_mode(make):
    cron = make("cron").handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = {t["name"] for t in cron["result"]["tools"]}
    assert names == {"check", "image_generate", "image_accept", "status", "wait"}
    inter = make().handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert {"fetch", "finish"} <= {t["name"] for t in inter["result"]["tools"]}


def test_cron_mode_refuses_fetch_and_finish(make):
    server = make("cron")
    for name in ("fetch", "finish"):
        response = call(server, name)
        assert not response["ok"] and response["error"]["code"] == "not_allowed"


@pytest.mark.parametrize("name,args", [
    ("image_generate", {"plan_id": "Bad Id"}),
    ("image_generate", {"plan_id": "ok", "repair_note": "x" * 2001}),
    ("image_generate", {"plan_id": "ok", "extra": 1}),
    ("image_accept", {"plan_id": "ok", "review": {"observed": "x"}}),
    ("wait", {}),
    ("status", {"student": "barna"}),
])
def test_invalid_params_give_structured_error(make, name, args):
    response = call(make(), name, args)
    assert not response["ok"] and response["error"]["code"] == "invalid_params"
    assert response["run_id"] == "20261003-0100-ab12" and response["log"].endswith(".log")


def test_unknown_tool_and_method(make):
    server = make()
    assert call(server, "rm_rf")["error"]["code"] == "unknown_tool"
    reply = server.handle({"jsonrpc": "2.0", "id": 9, "method": "resources/list"})
    assert reply["error"]["code"] == -32601
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_forced_exception_leaks_no_canary(make, log):
    def boom():
        raise RuntimeError(f"failed while reading {CANARY}")
    response = call(make(status=boom), "status")
    assert response["error"]["code"] == "internal_error"
    assert CANARY not in json.dumps(response)
    assert "Traceback" in log.main.read_text()


def test_results_and_owner_errors_are_redacted(make):
    response = call(make(status=lambda: {"note": f"token {CANARY} and sk-or-v1-{'a' * 40}"}),
                    "status")
    assert CANARY not in json.dumps(response) and "sk-or-v1" not in json.dumps(response)

    def blocked():
        raise NeedsOwner("conflict", todo="chat", details={"files": [f"wiki/{CANARY}.md"]})
    response = call(make(status=blocked), "status")
    assert response["error"]["code"] == "needs_owner" and CANARY not in json.dumps(response)


def test_background_job_and_wait_limit(make):
    def slow():
        time.sleep(2)
        return {"pushed": True}
    server = make(wait_s=0.3, finish=slow)
    started = call(server, "finish")
    job_id = started["result"]["job_id"]
    t0 = time.monotonic()
    pending = call(server, "wait", {"job_id": job_id})
    assert time.monotonic() - t0 < 1.5 and pending["result"]["state"] == "running"
    again = call(server, "fetch")  # a state-changing call while finish runs: same job
    assert again["result"]["job_id"] == job_id and again["result"]["already_running"]
    server.wait_s = 5
    done = call(server, "wait", {"job_id": job_id})
    assert done["result"] == {"job_id": job_id, "tool": "finish", "state": "done",
                              "result": {"pushed": True}}


def test_job_error_is_structured(make):
    def fails():
        raise NeedsOwner("rebase conflict", todo="resolve in chat",
                         details={"conflict_files": ["wiki/x.md"]})
    server = make(check=fails)
    done = finish_job(server, call(server, "check"))
    assert not done["ok"] and done["error"]["code"] == "needs_owner"
    assert done["error"]["conflict_files"] == ["wiki/x.md"]


def test_job_crash_leaks_no_canary(make):
    def crash():
        raise ValueError(CANARY)
    server = make(check=crash)
    done = finish_job(server, call(server, "check"))
    assert done["error"]["code"] == "internal_error" and CANARY not in json.dumps(done)


def test_image_generate_passes_arguments(make):
    server = make()
    done = finish_job(server, call(server, "image_generate", {"plan_id": "banner-1",
                                                              "repair_note": "nagyobb betű"}))
    assert done["result"]["result"] == {"plan_id": "banner-1", "note": "nagyobb betű"}


def test_wait_unknown_job(make):
    assert call(make(), "wait", {"job_id": "nope"})["error"]["code"] == "job_unknown"


def test_socket_roundtrip(make, tmp_path):
    sess = tmp_path / "sess"
    sess.mkdir(mode=0o700)
    server = make()
    stop = threading.Event()
    thread = threading.Thread(target=server.serve, args=(sess / "mcp.sock", stop.is_set))
    thread.start()
    try:
        for _ in range(50):
            if (sess / "mcp.sock").exists():
                break
            time.sleep(0.05)
        assert oct((sess / "mcp.sock").stat().st_mode & 0o777) == "0o600"
        with socket.socket(socket.AF_UNIX) as s:
            s.connect(str(sess / "mcp.sock"))
            stream = s.makefile("rwb")
            for msg in ({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                         "params": {"protocolVersion": "2025-06-18"}},
                        {"jsonrpc": "2.0", "method": "notifications/initialized"},
                        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                         "params": {"name": "status", "arguments": {}}}):
                stream.write(json.dumps(msg).encode() + b"\n")
            stream.write(b"not json\n")
            stream.flush()
            init = json.loads(stream.readline())
            status = json.loads(stream.readline())
            parse = json.loads(stream.readline())
        assert init["result"]["protocolVersion"] == "2025-06-18"
        assert status["result"]["structuredContent"]["result"] == {"phase": "writing"}
        assert parse["error"]["code"] == -32700
    finally:
        stop.set()
        thread.join(5)
    assert not (sess / "mcp.sock").exists()


def test_serve_refuses_a_shared_session_dir(make, tmp_path):
    sess = tmp_path / "open"
    sess.mkdir(mode=0o755)
    sess.chmod(0o755)
    with pytest.raises(PermissionError):
        make().serve(sess / "mcp.sock")


def test_every_call_is_logged_with_run_id(make, log):
    call(make(), "status")
    lines = [json.loads(x) for x in log.main.read_text().splitlines()]
    assert any(x["action"] == "mcp.status" and x["run_id"] == "20261003-0100-ab12" for x in lines)


def test_redact_patterns():
    text = ("-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY----- "
            "ya29.a0AfH6SMBxxxxxxxxx 1//0gabcdefghijklmnopqrstuv ghp_" + "a" * 36)
    out = redact({"k": [text]})
    assert "PRIVATE KEY" not in out["k"][0] and "ya29." not in out["k"][0]
    assert "1//0g" not in out["k"][0] and "ghp_" not in out["k"][0]
