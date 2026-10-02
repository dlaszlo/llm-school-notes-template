"""Generated blocks: `<!-- school-notes:generated <name> -->` … `<!-- /school-notes:generated -->`.

The same marker pair is used by the wiki generators; only the tool writes between them.
"""

import re

END = "<!-- /school-notes:generated -->"
BLOCK = re.compile(r"(<!-- school-notes:generated ([a-z0-9-]+) -->\n)(.*?)(" + re.escape(END) + ")",
                   re.S)


def start(name: str) -> str:
    return f"<!-- school-notes:generated {name} -->"


def blank(text: str) -> str:
    """The text with every generated block emptied (for diffs and the path guard)."""
    return BLOCK.sub(lambda m: m.group(1) + m.group(4), text)


def replace(text: str, name: str, content: str) -> str | None:
    """Replace the named block's content; None when the block is missing."""
    for m in BLOCK.finditer(text):
        if m.group(2) == name:
            body = content if content.endswith("\n") or not content else content + "\n"
            return text[:m.start(3)] + body + text[m.end(3):]
    return None


def block(name: str, content: str) -> str:
    body = content if content.endswith("\n") or not content else content + "\n"
    return f"{start(name)}\n{body}{END}\n"
