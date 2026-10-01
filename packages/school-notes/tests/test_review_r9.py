"""R9 early private manifest validation and exact owner-policy drift preflight."""
import json
from pathlib import Path
from unittest.mock import patch
import test_app as fixture
import test_review_r2 as r2
from school_notes import admin
from school_notes.common import Blocked

class R9Tests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor

    def test_N901_wiki_filter_config_drift_refuses_before_retry_then_repair(self):
        (self.repo/'.gitattributes').write_text('wiki/** filter=owner-wiki\n')
        self.git('add','.');self.git('commit','-m','Owner wiki policy');self.git('push','origin','HEAD:main')
        head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor()
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('blocked',job['state']);self.assertIn('wiki/',job['error']);self.assertIn('owner_policy_failure',job['payload'])
        self.git('config','owner.metadata','changed-after-wiki-policy-failure')
        before=job['payload'];dirs=list(supervisor.job_dir(job).glob('worktree*'));calls=list(supervisor.agents.calls)
        for _ in range(3):
            with self.assertRaisesRegex(Blocked,'acknowledge-maintenance'):admin.rebase_candidate(supervisor,job['id'])
            self.assertEqual(before,self.state.job(job['id'])['payload']);self.assertEqual(dirs,list(supervisor.job_dir(job).glob('worktree*')));self.assertEqual(calls,supervisor.agents.calls)
        self.assertTrue(job['payload']['owner_policy_failure']['path'].startswith('wiki/'))
        (self.repo/'.git/info/attributes').write_text('wiki/** -filter\n')
        admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error']);self.assertEqual(1,len(current['payload']['candidate_history']));self.assertTrue(Path(before['worktree']).exists())

    def missing_manifest(self,kind):
        path=self.repo/'publication/pilot.json';manifest=json.loads(path.read_text())
        if kind=='page':manifest['pages'][0]['path']='wiki/math/owner-missing-page.md'
        else:manifest['branding']={'light':{'path':'publication/assets/owner-missing-banner.png','sha256':'a'*64},'dark':{'path':'publication/assets/owner-missing-banner.png','sha256':'a'*64}}
        path.write_text(json.dumps(manifest)+'\n');self.git('add','.');self.git('commit','-m','Owner stale manifest');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor()
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('blocked',job['state']);self.assertEqual('candidate',job['phase']);self.assertIn('existing private manifest',job['error'])
        self.assertNotIn('worktree',job['payload']);self.assertEqual([],list(supervisor.job_dir(job).glob('worktree*')))
        self.assertFalse(any(p=='candidate' or p.startswith('source_review') for p in supervisor.agents.calls))
        self.assertEqual(manifest,json.loads(path.read_text()))

    def test_N902_missing_existing_page_blocks_before_worktree_or_model(self):self.missing_manifest('page')
    def test_N902_missing_existing_branding_blocks_before_worktree_or_model(self):self.missing_manifest('branding')
