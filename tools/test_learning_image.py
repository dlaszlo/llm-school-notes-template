"""Behavior checks for spending, versioning and review boundaries; no API calls."""
import base64
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
import learning_image as m


class ExecutorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        (self.repo / 'wiki/history').mkdir(parents=True)
        self.target = self.repo / 'wiki/history/topic.md'
        self.target.write_text('Verified lesson')
        self.config = {'request_id': 'trial', 'state_dir': str(self.root/'state'), 'max_total_usd': '1', 'reservation_usd': '.2', 'max_attempts': 3, 'learners': {'child': {'repo': str(self.repo), 'targets': ['wiki/history/topic.md'], 'max_usd': '1'}}}
        self.job = {'id': 'topic-banner', 'request_id': 'trial', 'learner': 'child', 'target': 'wiki/history/topic.md', 'role': 'banner', 'sources': [{'path':'wiki/history/topic.md','sha256':m.sha(self.target)}], 'plan': {'goal':'Understand', 'scope':'Scoped lesson', 'decision_reason':'Orientation', 'context':'Ancient place', 'composition':'Wide scene', 'visible_text':['Title'], 'claims':[{'text':'Verified fact','source':'lesson'}], 'style':'Clear', 'aspect_ratio':'21:9','constraints':'No inventions'}}
        self.path = self.root / 'job.json'
        self.save()
        self.calls = 0

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        m.write(self.path, self.job)

    def fake(self, payload, config):
        self.calls += 1
        out=io.BytesIO();Image.new('RGB',(420,180),(255-self.calls,255,255)).save(out,format='PNG')
        return {'usage':{'cost':.1},'data':[{'b64_json':base64.b64encode(out.getvalue()).decode(),'media_type':'image/png'}]}

    def generate(self, repair=None):
        return m.run_generate(self.config,self.path,repair,self.fake)

    def report(self, result, decision='accepted'):
        p=self.root/'review.json'
        m.write(p, {'sha256':result['sha256'],'verifier':'test','checked_at':m.now(),'observed':'Synthetic near-white test image, not teaching content','decision':decision,'checks':dict.fromkeys(m.CHECKS,'pass'),'material_defects':['test rejection'] if decision=='rejected' else []})
        return p

    def test_duplicate_does_not_spend_and_requires_review(self):
        r=self.generate();self.assertEqual(self.generate()['state'],'generated');self.assertEqual(self.calls,1)
        self.assertFalse((self.repo/'wiki/assets/banner/topic-banner.png').exists())
        m.review(self.config,self.path,self.report(r))
        self.assertTrue(self.generate()['reused']);self.assertEqual(self.calls,1)

    def test_stale_source_and_cross_learner_rejected(self):
        self.target.write_text('Changed')
        with self.assertRaises(ValueError):self.generate()
        self.job['sources'][0]['sha256']=m.sha(self.target);self.job['learner']='other';self.save()
        with self.assertRaises(KeyError):self.generate()
        self.assertEqual(self.calls,0)

    def test_path_escape_and_symlink_rejected(self):
        with self.assertRaises(ValueError):m.within(self.repo,'../outside')
        (self.repo/'escape').symlink_to(self.root)
        with self.assertRaises(ValueError):m.within(self.repo,'escape/file')

    def test_budget_blocks_before_request(self):
        self.config['max_total_usd']='.19'
        with self.assertRaises(ValueError):self.generate()
        self.assertEqual(self.calls,0)

    def test_timeout_preserves_unknown_and_blocks_other_jobs(self):
        def fail(payload,config):raise TimeoutError()
        with self.assertRaises(ValueError):m.run_generate(self.config,self.path,transport=fail)
        self.job['id']='topic-infographic';self.job['role']='infographic';self.save()
        with self.assertRaisesRegex(ValueError,'Reconcile'):self.generate()
        self.assertEqual(self.calls,0)

    def test_rename_cannot_reset_attempts(self):
        self.generate();self.job['id']='renamed';self.save()
        with self.assertRaisesRegex(ValueError,'original ID'):self.generate()
        self.assertEqual(self.calls,1)

    def test_three_attempt_limit_and_old_best_candidate(self):
        repair=self.root/'repair.txt';repair.write_text('Fix identified issue')
        first=None
        for n in range(3):
            r=self.generate(repair if n else None);first=first or r
            m.review(self.config,self.path,self.report(r,'rejected'))
        with self.assertRaisesRegex(ValueError,'Attempt bound'):self.generate(repair)
        self.assertEqual(self.calls,3)
        m.review(self.config,self.path,self.report(first))
        accepted=m.read(self.root/'state/ledger.json')['jobs'][self.job['id']]['accepted']
        self.assertEqual(accepted['attempt'],1)
        self.assertEqual(accepted['sha256'],first['sha256'])
        self.assertNotEqual(first['sha256'],r['sha256'])
        self.assertTrue(self.generate()['reused'])

    def test_review_hash_and_missing_checks_rejected(self):
        r=self.generate();p=self.report(r);v=m.read(p);v['sha256']='wrong';m.write(p,v)
        with self.assertRaises(ValueError):m.review(self.config,self.path,p)
        v['sha256']=r['sha256'];v['checks'].pop('context');m.write(p,v)
        with self.assertRaises(ValueError):m.review(self.config,self.path,p)

    def test_changed_plan_cannot_accept_old_image(self):
        r=self.generate();p=self.report(r)
        self.job['plan']['visible_text']=['Different claim'];self.save()
        with self.assertRaisesRegex(ValueError,'Job changed'):m.review(self.config,self.path,p)

    def test_reconcile_saved_response_without_network(self):
        r=self.generate()
        ledger_path=self.root/'state/ledger.json'
        ledger=m.read(ledger_path);ledger['jobs'][self.job['id']]['attempts'][0]['state']='unknown';m.write(ledger_path,ledger)
        fixed=m.reconcile(self.config,self.path)
        self.assertEqual(fixed['state'],'generated');self.assertEqual(self.calls,1)
        self.assertEqual(fixed['sha256'],r['sha256'])

    def test_concurrent_lock(self):
        with m.locked(self.config):
            with self.assertRaises(BlockingIOError):self.generate()
        self.assertEqual(self.calls,0)

    def test_no_private_paths_sent_to_provider(self):
        text=m.compile_prompt(self.job)
        self.assertNotIn(str(self.repo),text)
        self.assertNotIn('wiki/history',text)
        self.assertNotIn('child',text)


if __name__=='__main__':unittest.main()
