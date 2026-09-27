#!/usr/bin/env python3
"""Read-only comparison of the complete shared file set against a template checkout."""
import argparse
import hashlib
import json
from pathlib import Path


def read_manifest(root):
    data = json.loads((root / 'shared-files.json').read_text(encoding='utf-8'))
    paths = data['files']
    if not paths or len(paths) != len(set(paths)):
        raise ValueError('Shared file list is empty or contains duplicates')
    for name in paths:
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or str(p) != name:
            raise ValueError('Invalid shared path')
    return data


def compare(template, target):
    manifest = read_manifest(template)
    problems = []
    for name in manifest['files']:
        a, b = template / name, target / name
        if a.is_symlink() or b.is_symlink():
            problems.append(f'Not an ordinary shared file: {name}')
            continue
        if not a.resolve().is_relative_to(template.resolve()) or not b.resolve().is_relative_to(target.resolve()):
            problems.append(f'Shared path leaves its repository: {name}')
        elif not a.is_file() or not b.is_file():
            problems.append(f'Missing shared file: {name}')
        elif hashlib.sha256(a.read_bytes()).digest() != hashlib.sha256(b.read_bytes()).digest():
            problems.append(f'Different shared file: {name}')
    return manifest, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', type=Path, required=True, help='Canonical template checkout')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1], help='Wiki checkout to compare')
    args = parser.parse_args()
    try:
        manifest, problems = compare(args.template.resolve(), args.repo.resolve())
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'Cannot compare shared files: {exc}\n')
    if problems:
        parser.exit(1, '\n'.join(problems) + '\n')
    print(f"Shared files match: {len(manifest['files'])}; release {manifest['version']}")


if __name__ == '__main__':
    main()
