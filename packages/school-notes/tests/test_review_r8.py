"""R8 acquisition-bound sources and repaired noncommitted owner policy."""
from pathlib import Path
from unittest.mock import patch
import test_app as fixture
import test_review_r2 as r2
from school_notes import admin
from school_notes.common import Blocked,file_hash
from school_notes.verify import Git

class R8Tests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor

    def test_N802_wiki_owner_filter_source_preflight_passes_no_same_ack_retry(self):
        (self.repo/'.gitattributes').write_text('wiki/** filter=owner-wiki\n');self.git('add','.');self.git('commit','-m','Owner wiki-only policy');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor()
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertIn('owner_policy_failure',job['payload']);self.assertIn('wiki/',job['error']);self.assertTrue(job['payload']['git_sources'])
        main=Git(self.repo,supervisor.lock)
        for source in job['payload']['git_sources']:
            main.source_policy(str(Path(source['path']).relative_to(Path(job['payload']['worktree']))),source['path'])
        before=job['payload'];dirs=list(supervisor.job_dir(job).glob('worktree*'))
        for _ in range(3):
            with self.assertRaisesRegex(Blocked,'acknowledge-maintenance'):admin.rebase_candidate(supervisor,job['id'])
            self.assertEqual(before,self.state.job(job['id'])['payload']);self.assertEqual(dirs,list(supervisor.job_dir(job).glob('worktree*')))

    def bad_info_policy(self):
        path=self.repo/'.git/info/attributes';path.parent.mkdir(exist_ok=True);path.write_text('sources/** filter=owner-info\n');supervisor=self.supervisor()
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertIn('owner_policy_failure',job['payload'])
        return supervisor,job,path

    def test_N801_unbound_agent_crlf_source_is_candidate_repair(self):
        (self.repo/'.gitattributes').write_text('* text=auto eol=lf\n');self.git('add','.');self.git('commit','-m','Owner LF');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor()
        class WritesSource(fixture.FakeAgents):
            def call(inner,job,phase,envelope,cwd,*args,**kwargs):
                result,path=super().call(job,phase,envelope,cwd,*args,**kwargs)
                if phase=='candidate' and not job['payload'].get('candidate_history'):(Path(cwd)/'sources/agent-note.md').write_bytes(b'agent educational text\r\n')
                return result,path
        supervisor.agents=WritesSource(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertNotIn('owner_policy_failure',job['payload']);old=Path(job['payload']['worktree']);raw=(old/'sources/agent-note.md').read_bytes();admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        self.assertEqual('complete',self.state.job(job['id'])['state']);self.assertEqual(raw,(old/'sources/agent-note.md').read_bytes())

    def test_N801_agent_altered_bound_source_stops_before_review_and_repairs(self):
        supervisor=self.supervisor()
        class Alters(fixture.FakeAgents):
            def call(inner,job,phase,envelope,cwd,*args,**kwargs):
                result,path=super().call(job,phase,envelope,cwd,*args,**kwargs)
                if phase=='candidate' and not job['payload'].get('candidate_history'):
                    source=Path(job['payload']['git_sources'][0]['path']);source.write_bytes(source.read_bytes()+b'agent changed source')
                return result,path
        supervisor.agents=Alters(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('candidate',job['phase']);self.assertEqual('blocked',job['state']);self.assertFalse(any(p.startswith('source_review') for p in supervisor.agents.calls));self.assertNotIn('owner_policy_failure',job['payload']);old=Path(job['payload']['git_sources'][0]['path']);sha=file_hash(old);admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        self.assertEqual('complete',self.state.job(job['id'])['state']);self.assertEqual(sha,file_hash(old))

    def test_N802_info_policy_same_ack_repaired_preflight_allows_fresh_rebase(self):
        supervisor,job,path=self.bad_info_policy();before=job['payload'];dirs=list(supervisor.job_dir(job).glob('worktree*'));base=job['payload']['base']
        for _ in range(2):
            with self.assertRaises(Blocked):admin.rebase_candidate(supervisor,job['id'])
            self.assertEqual(before,self.state.job(job['id'])['payload']);self.assertEqual(dirs,list(supervisor.job_dir(job).glob('worktree*')))
        path.write_text('');admin.rebase_candidate(supervisor,job['id']);self.assertEqual(base,self.state.job(job['id'])['payload']['base'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state']);self.assertEqual(1,len(current['payload']['candidate_history']))

    def test_N802_resume_clears_stale_owner_flag_before_later_agent_violation(self):
        supervisor,job,path=self.bad_info_policy();path.write_text('');self.state.update_job(job['id'],'queued')
        class Deletes(fixture.FakeAgents):
            def call(inner,current,phase,envelope,cwd,*args,**kwargs):
                result,output=super().call(current,phase,envelope,cwd,*args,**kwargs)
                if phase=='candidate' and not current['payload'].get('candidate_history'):(Path(cwd)/'wiki/math/index.md').unlink()
                return result,output
        supervisor.agents=Deletes(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('blocked',current['state']);self.assertNotIn('owner_policy_failure',current['payload']);self.assertTrue(current['payload']['owner_policy_recoveries']);admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        self.assertEqual('complete',self.state.job(job['id'])['state']);self.assertTrue(self.state.job(job['id'])['payload']['owner_policy_recoveries'])
