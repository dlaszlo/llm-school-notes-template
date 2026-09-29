#!/usr/bin/env python3
"""Check rendered public files (including decompressed search data and PDF text).
Not a substitute for source/rights review. It records counts and offending filenames,
never writes matched secret text. Run: python3 check-public.py BUILD
"""
import gzip,json,re,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);payload=json.loads((root/'payload.json').read_text());assert payload['mode']=='public'
patterns=[r'/home/',r'file://',r'\b(?:sources|references|docs/evidence)/',r'OPENROUTER_API_KEY',r'client_secret_',r'image-description',r'Claude-Session:']
errors=[];counts={'files':0,'pdfs':0,'search_chunks':0}
for p in sorted((root/'site').rglob('*')):
 if not p.is_file():continue
 counts['files']+=1;b=p.read_bytes();text=None
 if p.suffix=='.pdf':counts['pdfs']+=1;text=subprocess.check_output(['pdftotext',str(p),'-'],text=True)
 elif p.suffix in ['.html','.svg','.xml','.json','.txt','.js','.css']:text=b.decode('utf8',errors='replace')
 elif p.suffix.startswith('.pf_'):
  # Pagefind compressed chunks are gzip streams.
  try:text=gzip.decompress(b).decode('utf8',errors='replace');counts['search_chunks']+=1
  except (OSError,EOFError):raise ValueError('Uninspected search chunk: '+p.name)
 if text is not None:
  for pattern in patterns:
   if re.search(pattern,text,re.I):errors.append({'file':p.relative_to(root/'site').as_posix(),'pattern':pattern})
 if p.suffix in ['.md','.pptx','.docx'] or 'receipt' in p.name:errors.append({'file':str(p.relative_to(root/'site')),'pattern':'private file type'})
result={'mode':'public',**counts,'errors':errors};(root/'privacy-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False));sys.exit(bool(errors))
