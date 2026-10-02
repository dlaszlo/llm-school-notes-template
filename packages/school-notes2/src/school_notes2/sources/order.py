"""The fixed page order (plan 4.3): file name in natural number order, full relative path for
subfolders, PDF pages in their own order. No ambiguity checks and no time-based fallback."""

import re

DIGITS = re.compile(r"(\d+)")


def natural_key(rel: str) -> tuple:
    """`2.jpg` < `10.jpg`; compared segment by segment, case-insensitively."""
    return tuple(tuple(int(part) if part.isdigit() else part.casefold()
                       for part in DIGITS.split(segment))
                 for segment in rel.split("/"))


def ordered(rels):
    return sorted(rels, key=lambda rel: (natural_key(rel), rel))
