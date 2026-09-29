import hashlib, importlib.util, io, json, tarfile, tempfile, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('bundle',Path(__file__).parents[1]/'release-bundle.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class BundleTests(unittest.TestCase):
 def test_public_only_pack_and_verify(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t); b=r/'build';(b/'site').mkdir(parents=True);(b/'site/index.html').write_text('Public')
   (b/'payload.json').write_text(json.dumps({'mode':'public','base':'/sample/','pages':[{}],'collections':[]}))
   (b/'browser-report.json').write_text(json.dumps({'errors':[],'pages':[{}]*6}))
   (b/'receipt.private.json').write_text('PRIVATE')
   (b/'privacy-report.json').write_text(json.dumps({'mode':'public','errors':[]}))
   mod.pack(b,r/'release','v1');mod.verify(r/'release/site.tar.gz',r/'out','/sample/','v1')
   self.assertEqual((r/'out/index.html').read_text(),'Public');self.assertFalse((r/'out/receipt.private.json').exists())
   with self.assertRaises(ValueError):mod.verify(r/'release/site.tar.gz',r/'bad','/other/','v1')
 def test_traversal_and_links_rejected(self):
  for name,link in [('../evil.html',False),('/evil.html',False),('safe.html',True)]:
   with tempfile.TemporaryDirectory() as t:
    r=Path(t);p=r/'site.tar.gz'
    with tarfile.open(p,'w:gz') as tar:
     for n in ['release.json',name]:
      info=tarfile.TarInfo(n);data=b'{}';info.size=len(data)
      if link and n==name:info.type=tarfile.SYMTYPE;info.linkname='/etc/passwd';info.size=0
      tar.addfile(info,io.BytesIO(data))
    (r/'site.tar.gz.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest())
    with self.assertRaises(ValueError):mod.verify(p,r/'out','/sample/','v1')
if __name__=='__main__':unittest.main()
