"""R10 agent manifest recovery and complete affected owner-policy preflight."""
import json
from pathlib import Path
from unittest.mock import patch
import test_app as fixture
import test_review_r2 as r2
from school_notes import admin
from school_notes.common import Blocked,file_hash

class R10Tests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor

    def bad_proposal(self,kind):
        if kind=='symlink':
            (self.repo/'wiki/math/alias.md').symlink_to('index.md');self.git('add','.');self.git('commit','-m','Owner existing alias');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
            with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor()
        class BadManifest(fixture.FakeAgents):
            def call(inner,job,phase,envelope,cwd,*args,**kwargs):
                result,path=super().call(job,phase,envelope,cwd,*args,**kwargs)
                if phase=='candidate' and not job['payload'].get('candidate_history'):
                    proposal=json.loads((Path(cwd)/'publication/pilot.json').read_text())
                    name='wiki/math/missing-proposal.md' if kind=='missing' else ('docs/evidence/bad.md' if kind=='nonwiki' else 'wiki/math/alias.md')
                    proposal['pages'].append({'path':name})
                    result['manifest_proposal']=proposal
                    # Preserve the actual returned result bytes as transport does.
                    path.write_text(json.dumps(result))
                return result,path
        supervisor.agents=BadManifest(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('blocked',job['state']);self.assertEqual('candidate',job['phase']);self.assertFalse(any(p.startswith('source_review') for p in supervisor.agents.calls))
        old=Path(job['payload']['worktree']);receipt=Path(job['payload']['candidate_result']);receipt_sha=file_hash(receipt)
        admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error']);self.assertEqual(1,len(current['payload']['candidate_history']));self.assertTrue(old.exists());self.assertEqual(receipt_sha,file_hash(receipt))
        self.assertEqual(job['payload']['agent_manifest_proposal'],current['payload']['candidate_history'][0]['agent_manifest_proposal'])

    def test_N1001_missing_proposal_before_review_same_ack_repair(self):self.bad_proposal('missing')
    def test_N1001_nonwiki_proposal_before_review_same_ack_repair(self):self.bad_proposal('nonwiki')
    def test_N1001_symlink_proposal_before_review_same_ack_repair(self):self.bad_proposal('symlink')

    def owner_block(self):
        (self.repo/'.gitattributes').write_text('wiki/** filter=owner-wiki\n');self.git('add','.');self.git('commit','-m','Owner wiki policy');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor()
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertIn('owner_policy_failure',job['payload'])
        return supervisor,job

    def test_N1002_partial_wiki_repair_config_drift_no_retry(self):
        supervisor,job=self.owner_block();first=job['payload']['owner_policy_failure']['path']
        (self.repo/'.git/info/attributes').write_text(first+' -filter\n');self.git('config','owner.metadata','partial-repair-drift')
        before=job['payload'];dirs=list(supervisor.job_dir(job).glob('worktree*'));calls=list(supervisor.agents.calls)
        for _ in range(3):
            with self.assertRaisesRegex(Blocked,'wiki/math/') as caught:admin.rebase_candidate(supervisor,job['id'])
            self.assertNotIn(first+' ',str(caught.exception))
            self.assertEqual(before,self.state.job(job['id'])['payload']);self.assertEqual(dirs,list(supervisor.job_dir(job).glob('worktree*')));self.assertEqual(calls,supervisor.agents.calls)
        (self.repo/'.git/info/attributes').write_text('wiki/** -filter\n');admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        self.assertEqual('complete',self.state.job(job['id'])['state'])

    def test_N1003_legacy_pathless_same_ack_refuses_without_allocation(self):
        supervisor,job=self.owner_block();payload=job['payload'];payload['owner_policy_failure'].pop('path');self.state.update_job(job['id'],payload=payload)
        self.git('config','owner.metadata','legacy-drift');dirs=list(supervisor.job_dir(job).glob('worktree*'))
        for _ in range(3):
            with self.assertRaisesRegex(Blocked,'exact failing path'):admin.rebase_candidate(supervisor,job['id'])
            self.assertEqual(payload,self.state.job(job['id'])['payload']);self.assertEqual(dirs,list(supervisor.job_dir(job).glob('worktree*')))
