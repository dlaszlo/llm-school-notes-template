"""Generate nine additional examples using existing local runtimes, no installer."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dot', required=True)
    ap.add_argument('--povray', required=True)
    ap.add_argument('--freecad-app-run', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    if out.exists():
        ap.error('Choose a new output directory')
    out.mkdir(parents=True)
    src = Path(__file__).resolve().parent
    record = {'runs':{}, 'source_sha256':{}}

    def execute(name, cmd, env=None):
        start = time.perf_counter()
        p = subprocess.run(cmd, cwd=out, env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        elapsed = time.perf_counter()-start
        log = p.stdout.decode(errors='replace')
        (out/(name+'.log')).write_text(log)
        if p.returncode:
            raise RuntimeError(name + ' failed; inspect its log')
        record['runs'][name] = {'seconds':elapsed}
        return log

    expected = {
        'quadratic': {'start->delta','delta->positive','positive->two','positive->zero','zero->one','zero->none'},
        'phases': {'solid->liquid','liquid->solid','liquid->gas','gas->liquid'},
        'web-request': {'browser->server','server->database','database->server','server->browser'},
    }
    for name, edges in expected.items():
        execute(name,[args.dot,'-Tsvg',str(src/(name+'.dot')),'-o',str(out/(name+'.svg'))])
        groups=ET.parse(out/(name+'.svg')).findall('.//{http://www.w3.org/2000/svg}g')
        actual={g.find('{http://www.w3.org/2000/svg}title').text for g in groups if g.attrib.get('class')=='edge'}
        assert {re.sub(r':[news]+(?=->|$)', '', e) for e in actual}==edges,(name,actual)
        record['runs'][name]['edge_check']=sorted(actual)
    execute('cad',[args.freecad_app_run,'freecadcmd','-u',str(out/'user.cfg'),'-s',str(out/'system.cfg'),str(src/'cad-more.py')],dict(os.environ,VISUAL_PILOT_OUTPUT=str(out)))
    record['cad_checks']=json.loads((out/'cad-checks.json').read_text())
    for name in ['ramps','pipe-cutaway','cube-section']:
        log=execute(name,[args.povray,'+I'+str(src/(name+'.pov')),'+O'+str(out/(name+'.png')),
                          '+W1200','+H800','+Q9','+A0.1','+WT2','-D','+FN'])
        assert (out/(name+'.png')).stat().st_size > 0
        record['runs'][name]['settings']={'width':1200,'height':800,'quality':9,'antialias':0.1,'threads':2}
        record['runs'][name]['scene_checks']=re.findall(r'CHECK[^\n]+',log)
        if name=='cube-section':
            pts=[tuple(map(float,p.split(','))) for p in re.findall(r'POINT ([-\d.,]+)',log)]
            assert len(pts)==6
            lengths=[]
            for i,p in enumerate(pts):
                assert abs(p[0]+p[1]-p[2]) < 1e-8
                assert max(map(abs,p))==1
                q=pts[(i+1)%6]; r=pts[(i-1)%6]
                a=tuple(q[j]-p[j] for j in range(3));b=tuple(r[j]-p[j] for j in range(3))
                length=math.sqrt(sum(x*x for x in a)); lengths.append(length)
                assert math.isclose(length, math.sqrt(2))
                assert math.isclose(sum(a[j]*b[j] for j in range(3))/(length*math.sqrt(sum(x*x for x in b))),-.5)
            record['runs'][name]['hexagon_check']={'points':pts,'side_lengths':lengths,'interior_angles_deg':120}
    for name in ['quadratic.dot','phases.dot','web-request.dot','cad-more.py','ramps.pov','pipe-cutaway.pov','cube-section.pov','more.py']:
        record['source_sha256'][name]=hashlib.sha256((src/name).read_bytes()).hexdigest()
    (out/'more-checks.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:round(v['seconds'],3) for k,v in record['runs'].items()}))


if __name__=='__main__':
    main()
