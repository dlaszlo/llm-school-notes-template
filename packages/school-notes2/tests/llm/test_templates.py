import tomllib
from importlib import resources

from school_notes2 import config

TEMPLATES = tomllib.loads(resources.files("school_notes2.llm").joinpath("templates.toml").read_text())


def parsed():
    data = {"email_to": "o@example.com", "git": {"name": "O", "email": "o@example.com"},
            "harnesses": TEMPLATES["harnesses"],
            "roles": {"writer": {"harness": "codex", "model": "gpt-6-astra", "effort": "high",
                                 "timeout_s": 5400},
                      "reviewer": {"harness": "claude-review", "model": "claude-opus-5-5",
                                   "effort": "high", "timeout_s": 600}}}
    return config.parse(data)


def test_templates_load_into_config():
    cfg = parsed()
    assert set(cfg.harnesses) == {"codex", "codex-review", "claude", "claude-review"}


def test_codex_approval_flag_precedes_exec_and_web_search_is_off():
    h = parsed().harnesses["codex"]
    assert h.headless.index("-a") < h.headless.index("exec")
    assert 'web_search="disabled"' in h.headless and 'web_search="disabled"' in h.interactive
    assert h.headless[-1] == "-" and h.prompt_stdin


def test_claude_has_no_positional_prompt_and_no_web_tools():
    for name in ("claude", "claude-review"):
        h = parsed().harnesses[name]
        assert h.headless[-3:] == ["--disallowedTools", "WebSearch", "WebFetch"]
        assert "--dangerously-skip-permissions" in h.headless


def test_reviewer_templates_have_no_mcp():
    cfg = parsed()
    for name in ("codex-review", "claude-review"):
        joined = " ".join(cfg.harnesses[name].headless)
        assert "mcp" not in joined
    for name in ("codex", "claude"):
        assert "UNIX-CONNECT:/run/sn/mcp.sock" in " ".join(cfg.harnesses[name].headless)
