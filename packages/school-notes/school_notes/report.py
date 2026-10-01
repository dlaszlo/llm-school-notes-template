"""Deterministic per-learner reports with an embedded Unicode TrueType font."""
import json
import struct
import unicodedata
import uuid
from pathlib import Path

from .common import Blocked, atomic_json, digest, private_dir


def pdf_bytes(lines, font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
    # Parse only the small sfnt tables required for glyph mapping/metrics.
    # No package installation or model call is needed for an offline report.
    font = Path(font_path).read_bytes()
    u16 = lambda offset: struct.unpack_from('>H', font, offset)[0]
    u32 = lambda offset: struct.unpack_from('>I', font, offset)[0]
    tables = {font[12+i*16:16+i*16].decode(): u32(20+i*16) for i in range(u16(4))}
    units = u16(tables['head']+18)
    metrics = u16(tables['hhea']+34)
    cmap = tables['cmap']
    mappings = []
    for i in range(u16(cmap+2)):
        offset = cmap + u32(cmap+4+i*8+4)
        if u16(offset) in (4,12):
            mappings.append(offset)
    def glyph(cp):
        for offset in sorted(mappings, key=lambda p:u16(p), reverse=True):
            if u16(offset) == 12:
                for i in range(u32(offset+12)):
                    first,last,gid = struct.unpack_from('>III',font,offset+16+i*12)
                    if first <= cp <= last:
                        return gid+cp-first
            elif cp <= 65535:
                count=u16(offset+6)//2
                ends=offset+14
                starts=ends+count*2+2
                deltas=starts+count*2
                ranges=deltas+count*2
                for i in range(count):
                    if u16(starts+i*2) <= cp <= u16(ends+i*2):
                        delta=u16(deltas+i*2)
                        ro=u16(ranges+i*2)
                        gid=u16(ranges+i*2+ro+(cp-u16(starts+i*2))*2) if ro else cp
                        return (gid+delta)%65536 if gid else 0
        return 0
    def advance(character):
        return u16(tables['hmtx']+min(glyph(ord(character)),metrics-1)*4)*9/units
    wrapped=[]
    for raw in lines:
        normalized = ''.join(c if c == '\n' or (not unicodedata.category(c).startswith('C') and glyph(ord(c))) else (' ' if c in '\t\r' else ('\\u%04X' % ord(c) if ord(c)<=65535 else '\\U%08X' % ord(c))) for c in str(raw))
        for line in normalized.split('\n'):
            remaining=line
            while remaining:
                width,end=0,0
                for character in remaining:
                    amount=advance(character)
                    if width+amount>523:
                        break
                    width+=amount
                    end+=1
                if end==0:
                    raise Blocked('report glyph wider than page')
                if end<len(remaining):
                    space=remaining.rfind(' ',0,end+1)
                    if space>0:
                        end=space
                wrapped.append(remaining[:end])
                remaining=remaining[end:].lstrip(' ')
            if not line:
                wrapped.append('')
    codes=sorted({ord(c) for line in wrapped for c in line})
    if len(codes)>65000:
        raise Blocked('report character set exceeds finite PDF font limit')
    cid={cp:i+1 for i,cp in enumerate(codes)}
    gids=b'\0\0'+b''.join(struct.pack('>H',glyph(cp)) for cp in codes)
    widths=' '.join(str(round(u16(tables['hmtx']+min(glyph(cp),metrics-1)*4)*1000/units)) for cp in codes)
    mapping=['/CIDInit /ProcSet findresource begin','12 dict begin','begincmap','/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def','/CMapName /SchoolNotesUnicode def','/CMapType 2 def','1 begincodespacerange','<0000> <FFFF>','endcodespacerange']
    for start in range(0,len(codes),100):
        group=codes[start:start+100]
        mapping += [f'{len(group)} beginbfchar']+[f'<{cid[cp]:04X}> <{chr(cp).encode("utf-16-be").hex()}>' for cp in group]+['endbfchar']
    mapping += ['endcmap','CMapName currentdict /CMap defineresource pop','end','end']
    stream=lambda data:b'<< /Length '+str(len(data)).encode()+b' >>\nstream\n'+data+b'\nendstream'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'',b'<< /Type /Font /Subtype /Type0 /BaseFont /SchoolNotes /Encoding /Identity-H /DescendantFonts [4 0 R] /ToUnicode 8 0 R >>',f'<< /Type /Font /Subtype /CIDFontType2 /BaseFont /SchoolNotes /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /FontDescriptor 5 0 R /CIDToGIDMap 7 0 R /W [1 [{widths}]] >>'.encode(),b'<< /Type /FontDescriptor /FontName /SchoolNotes /Flags 32 /FontBBox [-1021 -463 1793 1232] /ItalicAngle 0 /Ascent 928 /Descent -236 /CapHeight 730 /StemV 80 /FontFile2 6 0 R >>',stream(font),stream(gids),stream('\n'.join(mapping).encode())]
    kids=[]
    for start in range(0,max(len(wrapped),1),48):
        number=len(objects)+1
        kids.append(f'{number} 0 R')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {number+1} 0 R >>'.encode())
        commands=['BT /F1 9 Tf 36 806 Td 15 TL']
        for line in wrapped[start:start+48]:
            commands.append('<'+''.join(f'{cid[ord(c)]:04X}' for c in line)+'> Tj T*')
        objects.append(stream(('\n'.join(commands)+'\nET').encode()))
    objects[1]=f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'.encode()
    result=bytearray(b'%PDF-1.4\n')
    offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(result))
        result.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    start=len(result)
    result.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        result.extend(f'{offset:010d} 00000 n \n'.encode())
    result.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
    return bytes(result)


def semantic(status, learner=None):
    jobs=[{k:v for k,v in j.items() if k != 'updated'} for j in status['jobs'] if learner is None or j['learner']==learner]
    job_ids={j['id'] for j in jobs}
    observations={}
    for row in status['observations']:
        if learner is not None and row['learner'] != learner:
            continue
        key=(row['learner'],row['kind'])
        if key not in observations:
            observations[key]={k:v for k,v in row.items() if k not in ('id','created')}
    effects=[e for e in status['effects'] if not e['stable_key'].startswith('status-') and (learner is None or e.get('learner')==learner or e.get('job_id') in job_ids)]
    questions=[q for q in status['questions'] if learner is None or q['job_id'] in job_ids]
    packages=[p for p in status.get('packages',[]) if learner is None or p['learner']==learner]
    return {'scheduled_processing':status.get('scheduled_processing','available'),'packages':packages,'observations':sorted(observations.values(),key=lambda r:(r['learner'],r['kind'])),'jobs':jobs,'effects':effects,'questions':questions}


def write(status, directory, learner=None, font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
    directory=private_dir(directory)
    stable=semantic(status,learner)
    identifier=digest(stable)[:24]
    target=directory/f'allapot-{identifier}.pdf'
    if not target.exists():
        lines=['School Notes állapot', 'Learner: '+(learner or 'admin'), 'Report: '+identifier,'']
        lines.append('Scheduled processing: '+stable['scheduled_processing'])
        for package in stable['packages']:
            lines.append(f"Package {package['source_id']} {package['learner']}: {package['state']} / revision {package['current_seq']}")
        for job in stable['jobs']:
            lines.append(f"Job {job['id']} {job['learner']} {job['kind']}: {job['state']} / {job['phase']}")
            if job['error']:
                lines.append('Next step: '+job['error'])
        for effect in stable['effects']:
            lines.append(f"Effect {effect['kind']}: {effect['state']}")
        for q in stable['questions']:
            lines.extend([f"Question {q['id']} ({q['kind']} / {q['scope']}): {q['state']}",q['prompt']])
        data=pdf_bytes(lines,font_path)
        temporary=directory/(target.name+'.partial-'+str(uuid.uuid4()))
        with temporary.open('xb') as stream:
            import os
            os.chmod(temporary,0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,target)
        atomic_json(target.with_suffix('.json'),stable)
    atomic_json(directory/'latest.json',{'id':identifier,'pdf':str(target)})
    return target
