#!/usr/bin/env python3
"""Opt-in integration probe for a configured, disconnected Hermes Docker tutor.

Run with Hermes's Python runtime, from a Git checkout. No model/provider call,
installation or config mutation. Temporary synthetic fixtures are the only writes.
Uses installed Hermes internals deliberately: fail and re-audit on incompatibility.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import uuid
import zlib


def png():
    def chunk(kind, data):
        return (struct.pack('!I', len(data)) + kind + data
                + struct.pack('!I', zlib.crc32(kind + data)))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\0\xff\0\0')) + chunk(b'IEND', b''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-root', required=True, type=Path)
    parser.add_argument('--profile-home', required=True, type=Path)
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--other-repo', required=True, type=Path)
    args = parser.parse_args()
    home, snapshot, other = (p.resolve() for p in
                             (args.profile_home, args.snapshot, args.other_repo))
    if home.parent.name != 'profiles' or not (home / 'config.yaml').is_file():
        parser.error('Requires an existing non-default profile under profiles/')
    if snapshot == other or snapshot in other.parents or other in snapshot.parents:
        parser.error('Snapshot and other-repo must be separate checkouts')
    for root in (snapshot, other):
        if not (root / '.git').exists():
            parser.error('Both fixture roots must be Git checkouts')
    if (snapshot / '.env').exists():
        parser.error('Use a clean tutor snapshot without .env')
    os.environ['HERMES_HOME'] = str(home)
    sys.path.insert(0, str(args.hermes_root.resolve()))
    import hermes_bootstrap  # noqa: F401: installed runtime dependencies
    from hermes_cli.config import load_config_readonly, apply_terminal_config_to_env
    from hermes_cli.tools_config import _get_platform_tools
    cfg = load_config_readonly()
    terminal = cfg.get('terminal', {})
    expected_mount = f'{snapshot}:{snapshot}:ro'
    if (terminal.get('backend') != 'docker'
            or terminal.get('docker_volumes') != [expected_mount]
            or terminal.get('docker_network') is not False
            or terminal.get('docker_mount_cwd_to_workspace') is not False
            or terminal.get('docker_forward_env') != []):
        parser.error('Expected Docker, one read-only snapshot mount, no network/cwd mount/env forwarding')
    apply_terminal_config_to_env(config=cfg, override=True)
    os.chdir(snapshot)
    from model_tools import get_tool_definitions, handle_function_call
    from tools.image_source import resolve_image_source, ResolveContext, ImageResolutionError
    toolsets = sorted(_get_platform_tools(cfg, 'cli'))
    disabled = cfg.get('agent', {}).get('disabled_toolsets', [])
    definitions = get_tool_definitions(toolsets, disabled, quiet_mode=True,
                                       skip_tool_search_assembly=True)
    names = sorted(d.get('function', d)['name'] for d in definitions)
    permitted = {'read_file', 'write_file', 'patch', 'search_files', 'vision_analyze', 'clarify'}
    checks = {}
    checks['only_expected_tools'] = set(names) <= permitted
    checks['file_reader_available'] = 'read_file' in names
    if not all(checks.values()):
        print(json.dumps({'passed': False, 'tools': names, 'checks': checks}))
        return 1

    def call(name, **kwargs):
        result = handle_function_call(name, kwargs, task_id='default',
                                      enabled_tools=names, enabled_toolsets=toolsets,
                                      disabled_toolsets=disabled)
        return result if isinstance(result, str) else json.dumps(result)

    # Fixtures under .visual-runs are ignored by the notes repo. Nothing is staged.
    for root in (snapshot, other):
        (root / '.visual-runs').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tutor-probe-', dir=snapshot / '.visual-runs') as inside, \
         tempfile.TemporaryDirectory(prefix='tutor-probe-', dir=other / '.visual-runs') as sibling, \
         tempfile.TemporaryDirectory(prefix='tutor-host-canary-') as outside:
        dirs = [Path(inside), Path(sibling), Path(outside)]
        tokens = ['CANARY_' + uuid.uuid4().hex for _ in dirs]
        for directory, token in zip(dirs, tokens):
            (directory / 'canary.txt').write_text(token)
            (directory / 'canary.png').write_bytes(png())
        result = call('read_file', path=str(dirs[0] / 'canary.txt'))
        checks['snapshot_read'] = tokens[0] in result
        # Do not interpret an unavailable backend as a successful denial.
        if checks['snapshot_read']:
            result = call('write_file', path=str(dirs[0] / 'canary.txt'), content='MUTATED')
            checks['snapshot_write_denied'] = (
                (dirs[0] / 'canary.txt').read_text() == tokens[0]
                and ('error' in result.lower() or 'read-only' in result.lower()))
            for label, directory, token in zip(('sibling', 'host'), dirs[1:], tokens[1:]):
                result = call('read_file', path=str(directory / 'canary.txt'))
                checks[label + '_read_denied'] = token not in result and 'error' in result.lower()
            checks['skill_read'] = 'Study notes' in call(
                'read_file', path=str(snapshot / '.agents/skills/study-notes/SKILL.md'))
            for label, directory in zip(('snapshot', 'sibling', 'host'), dirs):
                try:
                    image = asyncio.run(resolve_image_source(
                        str(directory / 'canary.png'), ResolveContext(task_id='default')))
                    checks[label + '_image_' + ('read' if label == 'snapshot' else 'denied')] = (
                        label == 'snapshot' and image.data == png())
                except ImageResolutionError:
                    checks[label + '_image_' + ('read' if label == 'snapshot' else 'denied')] = label != 'snapshot'
        else:
            # Contains synthetic probe paths only, never a real secret's contents.
            print(json.dumps({'snapshot_read_error': result}))

        # Inspect only containers of this profile; do not change or stop others.
        ids = subprocess.check_output(['docker', 'ps', '-q', '--filter',
                                       f'label=hermes-profile={home.name}'], text=True).split()
        inspections = json.loads(subprocess.check_output(['docker', 'inspect', *ids], text=True)) if ids else []
        checks['container_found'] = bool(inspections)
        containers = []
        for item in inspections:
            mounts = [{k: m.get(k) for k in ('Source', 'Destination', 'RW')} for m in item['Mounts']]
            # The selected checkout and this fresh profile's own media caches only.
            mounts_ok = all((m['Source'] == str(snapshot) and not m['RW']) or
                            (Path(m['Source']).is_relative_to(home) and
                             Path(m['Source']).relative_to(home).parts[0] in
                             {'cache', 'images', 'image_cache', 'audio_cache', 'video_cache',
                              'temp_vision_images', 'temp_video_files'}) for m in mounts)
            env_names = sorted(e.split('=', 1)[0] for e in item['Config'].get('Env', []))
            checks['mounts_and_network_' + item['Id'][:12]] = (
                mounts_ok and any(m['Source'] == str(snapshot) and not m['RW'] for m in mounts)
                and item['HostConfig']['NetworkMode'] == 'none'
                and not item['HostConfig'].get('Privileged'))
            containers.append({'id': item['Id'][:12], 'mounts': mounts,
                               'network': item['HostConfig']['NetworkMode'], 'env_names': env_names})
    report = {'passed': all(checks.values()), 'checks': checks, 'tools': names,
              'containers': containers, 'config_sha256': hashlib.sha256((home / 'config.yaml').read_bytes()).hexdigest(),
              'limits': 'No model call; image resolver tested, not semantic vision. CLI conversational pilot required.'}
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
