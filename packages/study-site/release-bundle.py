#!/usr/bin/env python3
"""Package a reviewed public build, or verify/extract it for GitHub Pages.
No private repository is used by the deployment job. Python standard library only.
"""
import hashlib, io, json, re, sys, tarfile
from pathlib import Path, PurePosixPath

def digest(b): return hashlib.sha256(b).hexdigest()
def allowed(name):
    p=PurePosixPath(name)
    return (not p.is_absolute() and '..' not in p.parts and not any(s.startswith('.') for s in p.parts)
            and p.suffix.lower() in {'.html','.css','.js','.mjs','.json','.xml','.txt','.svg','.png','.webp','.jpg','.jpeg','.gif','.woff2','.woff','.pdf','.pf_fragment','.pf_index','.pf_meta','.pagefind','.wasm'})

def pack(build, output, tag):
    build=Path(build);output=Path(output);output.mkdir(parents=True,exist_ok=False)
    payload=json.loads((build/'payload.json').read_text())
    checks=json.loads((build/'browser-report.json').read_text())
    privacy=json.loads((build/'privacy-report.json').read_text())
    if privacy.get('mode')!='public' or privacy.get('errors') != []:raise ValueError('Successful public privacy check required')
    if payload['mode']!='public' or checks['errors'] or len(checks['pages'])!=len(payload['pages'])*6:
        raise ValueError('A public build with complete successful browser checks is required')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}',tag):raise ValueError('Invalid release tag')
    site=build/'site';entries={}
    for f in sorted(site.rglob('*')):
        if f.is_symlink():raise ValueError('No symlinks')
        if not f.is_file():continue
        name=f.relative_to(site).as_posix()
        if not allowed(name) or name=='release.json':raise ValueError('Unexpected public file: '+name)
        entries[name]=f.read_bytes()
    record={'schema':1,'release':tag,'base':payload['base'],'pages':len(payload['pages']),'pdfs':sum(bool(c.get('pdf')) for c in payload['collections']),'files':{n:digest(b) for n,b in entries.items()}}
    entries['release.json']=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode()
    archive=output/'site.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for name,data in entries.items():
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0
            tar.addfile(info,io.BytesIO(data))
    (output/'site.tar.gz.sha256').write_text(digest(archive.read_bytes())+'  site.tar.gz\n')
    print(json.dumps({'release':tag,'files':len(entries),'bytes':archive.stat().st_size,'pages':record['pages'],'pdfs':record['pdfs']}))

def verify(archive, output, base, tag):
    archive=Path(archive);output=Path(output)
    expected=archive.with_name('site.tar.gz.sha256').read_text().split()[0]
    if not re.fullmatch('[a-f0-9]{64}',expected) or digest(archive.read_bytes())!=expected:raise ValueError('Archive hash mismatch')
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers()
        if len(members)>30000 or sum(m.size for m in members)>1024**3:raise ValueError('Oversized release')
        names=[m.name for m in members]
        if len(names)!=len(set(names)) or 'release.json' not in names:raise ValueError('Missing manifest or duplicate file')
        if any(not m.isfile() or not allowed(m.name) for m in members):raise ValueError('Unsafe archive member')
        manifest=json.load(tar.extractfile('release.json'))
        if manifest['schema']!=1 or manifest['release']!=tag or manifest['base']!=base:raise ValueError('Release identity mismatch')
        if set(manifest['files'])!=set(names)-{'release.json'}:raise ValueError('Inventory mismatch')
        for m in members:
            data=tar.extractfile(m).read()
            if m.name!='release.json' and digest(data)!=manifest['files'][m.name]:raise ValueError('File hash mismatch: '+m.name)
        output.mkdir(parents=True,exist_ok=False)
        for m in members:
            target=output/m.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
    print('Verified public release '+tag)

if __name__=='__main__':
    if sys.argv[1]=='pack':pack(*sys.argv[2:])
    elif sys.argv[1]=='verify':verify(*sys.argv[2:])
    else:raise ValueError('Use pack BUILD OUTPUT TAG or verify ARCHIVE OUTPUT BASE TAG')
