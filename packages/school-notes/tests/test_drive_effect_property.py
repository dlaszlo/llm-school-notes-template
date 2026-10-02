"""Offline Drive metadata/reconciliation regressions; no authentication/network."""
import copy
import hashlib
from pathlib import Path
import tempfile
import types
import unittest

from school_notes.common import Blocked, digest, file_hash
from school_notes.drive import API, FOLDER, DriveAPI, effect_property


class EffectPropertyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'original.jpg';self.path.write_bytes(b'synthetic original bytes')
        self.sha=file_hash(self.path);self.calls=[];self.files={};self.pending=None
        self.api=object.__new__(DriveAPI);self.api.window=None
        self.api.module=types.SimpleNamespace(allowed_url=lambda _:None)
        self.api.metadata=lambda identity:copy.deepcopy(self.files[identity])
        self.api.download_hash=lambda identity:(self.sha,self.path.stat().st_size)
        self.api.request=self.request

    def request(self,method,url,data=None,headers=None):
        self.calls.append((method,url,copy.deepcopy(data)))
        if method=='POST':
            for key,value in data['appProperties'].items():
                self.assertLessEqual(len(key.encode('utf-8'))+len(value.encode('utf-8')),124,
                                     'actual metadata sent to Drive exceeds property limit')
            self.files[data['id']]=copy.deepcopy(data)
            if url.startswith(API+'/files'):
                return 200,{},copy.deepcopy(data)
            self.pending=data['id']
            return 200,{'Location':'https://www.googleapis.com/upload/synthetic-session'},{}
        self.assertEqual(method,'PUT')
        self.assertEqual(data,self.path.read_bytes())
        return 200,{},copy.deepcopy(self.files[self.pending])

    def effect(self,key,identity='fixed-original'):
        return {'external_id':identity,'target':'fixed-parent','stable_key':key,'artifact_hash':self.sha}

    def test_long_upload_metadata_is_bounded_and_reconcile_retains_full_original_key_and_id(self):
        key='archive-original:'+('a'*64)+':'+('b'*64)
        effect=self.effect(key);before=copy.deepcopy(effect)
        uploaded=self.api.upload(effect['external_id'],self.path,'image/jpeg',effect['target'],key,self.sha)
        expected=hashlib.sha256(key.encode('utf-8')).hexdigest()
        self.assertEqual(uploaded['appProperties'],{'school_notes_effect':expected,'sha256':self.sha})
        self.assertEqual(len(expected),64)
        self.assertEqual(self.calls[0][2]['id'],'fixed-original')
        self.assertEqual(self.calls[0][2]['parents'],['fixed-parent'])
        reconciled=self.api.reconcile(effect)
        self.assertEqual(reconciled,{'verified':True,'external_id':'fixed-original','target':'fixed-parent','sha256':self.sha})
        self.assertEqual(effect,before)

    def test_utf8_exact_byte_limit_keeps_old_value_one_more_byte_hashes(self):
        budget=124-len(b'school_notes_effect')
        exact='é'*(budget//2)+'x'*(budget%2)
        self.assertEqual(len(exact.encode('utf-8'))+len(b'school_notes_effect'),124)
        self.assertEqual(effect_property(exact),exact)
        longer=exact+'x'
        self.assertLess(len(longer),budget)
        self.assertEqual(effect_property(longer),hashlib.sha256(longer.encode('utf-8')).hexdigest())
        self.api.upload('fixed-original',self.path,'image/jpeg','fixed-parent',longer,self.sha)
        self.assertEqual(self.calls[0][2]['appProperties']['school_notes_effect'],effect_property(longer))

    def test_short_existing_folder_property_is_unchanged_and_reconciles(self):
        key='archive-folder:short-old-key'
        created=self.api.create_folder('fixed-folder','Originals','fixed-parent',key)
        self.assertEqual(created['appProperties'],{'school_notes_effect':key})
        effect={'external_id':'fixed-folder','target':'fixed-parent','stable_key':key,
                'artifact_hash':digest({'name':'Originals','parent':'fixed-parent'})}
        self.assertTrue(self.api.reconcile(effect,folder=True)['verified'])

    def test_long_folder_property_uses_same_mapping_as_upload_and_reconcile(self):
        key='folder:'+'árvíztűrő'*30
        created=self.api.create_folder('fixed-folder','Originals','fixed-parent',key)
        self.assertEqual(created['appProperties']['school_notes_effect'],hashlib.sha256(key.encode('utf-8')).hexdigest())
        self.assertEqual(created['mimeType'],FOLDER)
        effect={'external_id':'fixed-folder','target':'fixed-parent','stable_key':key,
                'artifact_hash':digest({'name':'Originals','parent':'fixed-parent'})}
        self.assertEqual(self.api.reconcile(effect,folder=True)['external_id'],'fixed-folder')

    def test_reconcile_rejects_wrong_external_id_parent_or_effect_property(self):
        key='original:'+('e'*140)
        self.api.upload('fixed-original',self.path,'image/jpeg','fixed-parent',key,self.sha)
        original=copy.deepcopy(self.files['fixed-original'])
        variants=[{'id':'different-file'},{'parents':['different-parent']},
                  {'appProperties':{'school_notes_effect':effect_property('other:'+('e'*140)),'sha256':self.sha}}]
        for altered in variants:
            with self.subTest(altered=altered):
                self.files['fixed-original']={**original,**altered}
                with self.assertRaisesRegex(Blocked,'target/ownership mismatch'):
                    self.api.reconcile(self.effect(key))

    def test_short_legacy_upload_property_still_reconciles_without_remapping(self):
        key='old-short-key'
        self.api.upload('fixed-original',self.path,'image/jpeg','fixed-parent',key,self.sha)
        self.assertEqual(self.files['fixed-original']['appProperties']['school_notes_effect'],key)
        self.assertTrue(self.api.reconcile(self.effect(key))['verified'])


if __name__=='__main__':unittest.main()
