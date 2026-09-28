"""Optional local benchmark; uses supplied executables, never installs anything.

Write results outside the checkout. Python standard library only.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import time
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dot')
    parser.add_argument('--povray')
    parser.add_argument('--freecad', help='FreeCADCmd/freecadcmd executable')
    parser.add_argument('--freecad-app-run', help='Extracted official AppImage AppRun, alternative to --freecad')
    parser.add_argument('--ffmpeg', help='Optional encoder for the 25-frame POV-Ray sequence')
    args = parser.parse_args()
    if args.freecad and args.freecad_app_run:
        parser.error('Choose one FreeCAD entry point')
    if not (args.dot or args.povray or args.freecad or args.freecad_app_run):
        parser.error('Supply at least one executable')
    out = args.output.resolve()
    if out.exists():
        parser.error('Output must be new, to prevent stale artifacts from passing checks')
    out.mkdir(parents=True)
    source = Path(__file__).resolve().parent
    result = {'platform': platform.platform(), 'logical_cpus': os.cpu_count(),
              'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in source.iterdir() if p.suffix in ('.py', '.pov', '.dot')},
              'runs': {}}

    def execute(name, command, env=None):
        start = time.perf_counter()
        p = subprocess.run(command, cwd=out, env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        elapsed = time.perf_counter() - start
        log = p.stdout.decode('utf-8', errors='replace')
        (out / f'{name}.log').write_text(log)
        if p.returncode:
            raise RuntimeError(f'{name} exited {p.returncode}: see log')
        return elapsed, log

    if args.dot:
        times = []
        _, version = execute('graphviz-version', [args.dot, '-V'])
        for i in range(3):
            elapsed, _ = execute(f'graphviz-{i}', [args.dot, '-Tsvg', str(source/'structure.dot'), '-o', str(out/f'structure-{i}.svg')])
            times.append(elapsed)
            root = ET.parse(out/f'structure-{i}.svg').getroot()
            groups = root.findall('.//{http://www.w3.org/2000/svg}g')
            actual = {g.find('{http://www.w3.org/2000/svg}title').text
                      for g in groups if g.attrib.get('class') == 'edge'}
            assert actual == {'force->magnitude', 'force->direction', 'force->application', 'force->action'}
        result['runs']['graphviz'] = {'seconds': times, 'median_seconds': statistics.median(times), 'version': version.strip(), 'edge_check': 'four expected edges in exported SVG'}

    if args.freecad or args.freecad_app_run:
        command = [args.freecad] if args.freecad else [args.freecad_app_run, 'freecadcmd']
        times, checks = [], []
        for i in range(3):
            dest = out / f'freecad-{i}'
            env = dict(os.environ, VISUAL_PILOT_OUTPUT=str(dest))
            elapsed, _ = execute(f'freecad-{i}', command + ['-u', str(out/f'user-{i}.cfg'), '-s', str(out/f'system-{i}.cfg'), str(source/'gear.py')], env)
            # Some FreeCAD script exceptions do not produce a nonzero exit status.
            checks.append(json.loads((dest/'gear-checks.json').read_text()))
            for name in ('gear.FCStd', 'gear.step', 'gear.svg'):
                assert (dest/name).stat().st_size > 0
            times.append(elapsed)
        result['runs']['freecad'] = {'seconds': times, 'median_seconds': statistics.median(times), 'checks': checks}

    if args.povray:
        base = [args.povray, '+I'+str(source/'lever.pov'), '+W960', '+H640', '+Q9', '+A0.1', '+WT2', '-D', '+FN']
        times = []
        for i in range(3):
            elapsed, _ = execute(f'povray-static-{i}', base + ['+O'+str(out/f'lever-{i}.png'), '+K0.5'])
            times.append(elapsed)
        elapsed, log = execute('povray-animation', base + ['+O'+str(out/'frame.png'), '+KFI1', '+KFF25', '+KI0', '+KF1'])
        frames = sorted(out.glob('frame*.png'))
        assert len(frames) == 25
        observed = re.findall(r'CHECK theta_deg=([-\d.]+) x=([-\d.]+) y=([-\d.]+)', log)
        assert len(observed) == 25
        for index, values in enumerate(observed):
            angle, x, y = map(float, values)
            assert abs(angle - (-45 + 90*index/24)) < 1e-5
            assert abs(x*x+y*y-1) < 1e-8
            assert abs(x-math.cos(math.radians(angle))) < 1e-8
            assert abs(y-math.sin(math.radians(angle))) < 1e-8
        result['runs']['povray'] = {'static_seconds': times, 'static_median_seconds': statistics.median(times),
                                   'sequence_seconds': elapsed, 'frames': 25, 'size': [960, 640],
                                   'quality': 9, 'antialias': 0.1, 'threads': 2,
                                   'checks': '25 emitted poses: angle, fixed length and horizontal moment arm; not a dynamics simulation'}
        if args.ffmpeg:
            elapsed, _ = execute('encode', [args.ffmpeg, '-nostdin', '-v', 'error', '-framerate', '12', '-i', str(out/'frame%02d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(out/'lever.mp4')])
            result['runs']['povray']['encoding_seconds'] = elapsed
    (out/'timings.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: {k: v for k, v in data.items() if 'seconds' in k} for key, data in result['runs'].items()}, indent=2))


if __name__ == '__main__':
    main()
