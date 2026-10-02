"""Reading a role's JSON output (plan 4.7): `file` mode reads the named file, `stdout` mode
finds the schema-valid JSON object in the harness text without parsing its envelope."""

import json
from pathlib import Path

from ..schemas import errors

SCAN_LIMIT = 400_000   # only the tail of a long transcript is searched


def read_file(path: Path, schema: str) -> tuple[dict | None, list[str]]:
    """The output file's object and its schema problems; (None, [why]) when unusable."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"{path.name} is missing"]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, [f"{path.name} is not valid JSON: {exc}"]
    problems = errors(schema, value)
    return (value, []) if not problems else (None, problems)


def extract_stdout(text: str, schema: str) -> tuple[dict | None, list[str]]:
    """The last JSON object in `text` that satisfies `schema`."""
    tail = text[-SCAN_LIMIT:]
    decoder = json.JSONDecoder()
    position = len(tail)
    while (position := tail.rfind("{", 0, position)) != -1:
        try:
            value, _ = decoder.raw_decode(tail, position)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and not errors(schema, value):
            return value, []
    return None, [f"no JSON object matching the {schema} schema in the output"]
