"""The one-time v1 → v2 migration of a learner repo (plan 11/3).

    python -m school_notes2.migration <worktree> --original <untouched copy> --report <file>

Runs on a worktree of the learner repo; nothing is committed. It derives `chapters`,
`chapter`/`order` and `lessons`, writes the generated blocks, regenerates the indexes, the
review index and public.json (every page; no omitSections/publicEdits), deletes pilot.json,
and writes the T1 difference list that the owner approves before the commit."""

import argparse
import json
import sys
from pathlib import Path

from .review import index as review_index
from .wiki import compare, generate, migrate, public


def run(repo: Path, original: Path) -> dict:
    mig = migrate.migrate(repo)
    lesson_type = _lesson_type_problems(repo)
    generate.write_indexes(repo)
    review_index.update(repo)
    rights = public.render_rights(repo)
    diff = compare.report(original, repo, rights)
    if not diff["unknown_assets"]:
        public.write(repo, rights)
    pilot = repo / "publication" / "pilot.json"
    if pilot.exists():
        pilot.unlink()
    return {"warnings": mig.warnings, "lesson_type": lesson_type, **diff}


def _lesson_type_problems(repo: Path) -> list[str]:
    """11/3: every `-jegyzet.md` page must be `type: lesson-notes`."""
    from .wiki import frontmatter
    out = []
    for path in sorted((repo / "wiki").glob("*/*-jegyzet.md")):
        meta = frontmatter.split(path.read_text(encoding="utf-8")).meta
        if meta.get("type") != "lesson-notes":
            out.append(f"{path.relative_to(repo).as_posix()}: type is {meta.get('type')!r}")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m school_notes2.migration")
    p.add_argument("worktree", type=Path)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args(argv)
    result = run(args.worktree, args.original)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    identical = not (result["indexes"] or result["publication"] or result["unknown_assets"])
    print("identical" if identical else f"differences: {len(result['indexes'])} index file(s), "
          f"{len(result['publication'])} publication line(s), "
          f"{len(result['unknown_assets'])} asset(s) without rights", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
