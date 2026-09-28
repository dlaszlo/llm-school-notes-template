#!/usr/bin/env python3
"""Bind the Git checkout's image skill into Hermes; no secrets or paid calls."""
import argparse
from pathlib import Path
import subprocess


def install(repo, hermes_home, check=False):
    repo = Path(repo).resolve()
    relative = 'integrations/hermes/learning-images/SKILL.md'
    source = repo / relative
    committed = subprocess.check_output(['git', 'show', 'HEAD:' + relative], cwd=repo)
    if source.read_bytes() != committed:
        raise ValueError('Commit the skill first; deployment uses committed Git content only')
    target = Path(hermes_home).expanduser().absolute() / 'skills/learning-images/SKILL.md'
    if target.is_symlink() and target.resolve() == source:
        return 'already linked'
    if target.exists() or target.is_symlink():
        raise ValueError('Existing skill differs from the expected link; inspect and preserve it before migration')
    if check:
        raise ValueError('Skill is not installed from this checkout')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source)
    return 'linked'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home', required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    try:
        print(install(repo, args.hermes_home, args.check))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
