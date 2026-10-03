"""Reading a role's JSON output (plan 4.7): `file` mode reads the named file, `stdout` mode
finds the schema-valid JSON object in the harness text without parsing its envelope."""

import json
from pathlib import Path

from ..schemas import errors
from ..state import safefs

SCAN_LIMIT = 400_000   # only the tail of a long transcript is searched


def read_file(path: Path, schema: str, root: Path | None = None) -> tuple[dict | None, list[str]]:
    """The output file's object and its schema problems; (None, [why]) when unusable.

    `root` is the container-controlled tree the file lies in (the worktree or out/): the
    file is then read without following any symlink (plan 7.6)."""
    root = root or path.parent
    try:
        value = json.loads(safefs.read_text(root, safefs.rel_of(root, path)))
    except FileNotFoundError:
        return None, [f"{path.name} is missing"]
    except safefs.UnsafePath as exc:
        return None, [f"{path.name}: {exc}"]
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
