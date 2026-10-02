"""Best-effort metrics from a harness transcript (plan 5.3, K12). Never raises: a missing
number is only a missing number."""

import json
from pathlib import Path

KEYS = ("input_tokens", "output_tokens", "cached_input_tokens", "cache_read_input_tokens",
        "cache_creation_input_tokens")


def _events(text: str):
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                yield value


def _usage(usage) -> dict:
    if not isinstance(usage, dict):
        return {}
    return {k: usage[k] for k in KEYS if isinstance(usage.get(k), (int, float))}


def _add(total: dict, part: dict) -> None:
    for key, value in part.items():
        total[key] = total.get(key, 0) + value


def from_transcript(path: Path) -> dict:
    """Claude Code stream-json: the final `result` event; Codex --json: summed turn usages."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        final, turns = {}, {}
        for event in _events(text):
            kind = event.get("type")
            if kind == "result":
                final = _usage(event.get("usage"))
                if isinstance(event.get("total_cost_usd"), (int, float)):
                    final["cost_usd"] = event["total_cost_usd"]
                if isinstance(event.get("num_turns"), int):
                    final["turns"] = event["num_turns"]
            elif kind == "turn.completed":
                _add(turns, _usage(event.get("usage")))
        return final or turns
    except Exception:  # noqa: BLE001 - metrics must never fail a run
        return {}
