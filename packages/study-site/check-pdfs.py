#!/usr/bin/env python3
"""Render all final PDF pages and create numbered contact sheets for visual review.
Requires system Poppler and Pillow (the template's uv environment).
Usage: uv run packages/study-site/check-pdfs.py SITE/pdf OUTSIDE_QA_DIRECTORY
"""
import concurrent.futures, hashlib, json, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
source, output=map(Path,sys.argv[1:]); output.mkdir(parents=True,exist_ok=False)
def render(item):
    i,p=item; prefix=output/f'{i:02d}'
    text=subprocess.check_output(['pdftotext',str(p),'-'],text=True)
    info=subprocess.check_output(['pdfinfo',str(p)],text=True)
    pages=int(re.search(r'Pages:\s+(\d+)',info)[1])
    subprocess.run(['pdftoppm','-scale-to','1100','-png',str(p),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    return dict(number=i,file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pages=pages,text_characters=len(text),has_replacement_character='\ufffd' in text,license_on_every_page=all('CC BY-NC-SA 4.0' in t for t in text.split('\f') if t.strip()))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    records=list(pool.map(render,enumerate(sorted(source.glob('*.pdf')),1)))
images=sorted(output.glob('*.png'),key=lambda p:tuple(map(int,p.stem.split('-'))))
for batch in range(0,len(images),12):
    board=Image.new('RGB',(1800,2160),'#bbbbbb');d=ImageDraw.Draw(board)
    for j,p in enumerate(images[batch:batch+12]):
        im=Image.open(p).convert('RGB'); im.thumbnail((442,686)); x=(j%4)*450;y=(j//4)*720
        board.paste(im,(x,y+24));d.text((x+6,y+5),p.stem,fill='black')
    board.save(output/f'board-{batch//12+1:02d}.jpg',quality=88)
(output/'manifest.json').write_text(json.dumps({'documents':records,'pages':len(images)},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pdfs':len(records),'pages':len(images),'boards':(len(images)+11)//12,'text_errors':[r['file'] for r in records if r['has_replacement_character'] or not r['license_on_every_page']]}))
