"""R12 adapter recursion, byte-faithful names, atomic retention and quota markers."""
import json
import os
from pathlib import Path
import sqlite3
import sys
from unittest.mock import patch
import test_app as f
import test_review_r2 as r2
from school_notes import admin
from school_notes.agents import Agent
from school_notes.common import Blocked,Window,atomic_json,file_hash

class R12Tests(f.Base):
    setUp=f.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor

    def actual_transport(self,mode):
        supervisor=self.supervisor();config=json.loads((f.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable
        agent=Agent(config,self.state,supervisor.lock,Window());proof=self.root/'synthetic-only.json';atomic_json(proof,{'synthetic_transport_only':True});settings=agent.role_settings('codex');settings.update(evidence=str(proof),timeout=30,argv=[sys.executable,'-c','pass','{result}'])
        class Transport(f.FakeAgents):
            def call(inner,job,phase,envelope,cwd,directory,instructions):
                if phase!='candidate':return super().call(job,phase,envelope,cwd,directory,instructions)
                def provider(argv,execution_cwd,**kwargs):
                    Path(str(kwargs['log'])+'.stderr').write_text('')
                    response,_=super(Transport,inner).call(job,phase,envelope,cwd,directory,instructions)
                    if mode=='deep' and not job['payload'].get('candidate_history'):
                        response['manifest_proposal']='['*200000;response['status']='question';response['uncertainties']=['Retain uncertainty alongside malformed manifest']
                    else:response['manifest_proposal']=json.dumps(response['manifest_proposal'])
                    attempt=Path(argv[-1]).parent;atomic_json(attempt/'result.json',response)
                    events=[{'type':'item.completed','item':{'type':'agent_message','text':'Source quotes quota_exceeded as instructional text'}},{'type':'turn.completed'}]
                    Path(kwargs['log']).write_text('\n'.join(json.dumps(e) for e in events)+'\n')
                with patch.object(agent,'_gate',return_value=settings),patch('school_notes.agents.run',provider):return agent.call(job,phase,envelope,cwd,directory,instructions)
        supervisor.agents=Transport(self.state,supervisor.lock)
        return supervisor

    def test_N1201_deep_manifest_actual_call_retained_and_same_ack_completes(self):
        supervisor=self.actual_transport('deep')
        with patch('school_notes.pipeline.Renderer',f.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertNotIn('quota_block',job['payload']);receipt=job['payload']['invalid_manifest_attempt'];self.assertEqual('question',receipt['status']);self.assertEqual(['Retain uncertainty alongside malformed manifest'],receipt['uncertainties']);self.assertEqual('failed',self.state.rows('SELECT state FROM attempts')[0]['state']);self.assertEqual(file_hash(receipt['path']),receipt['sha256']);self.assertFalse(any(p.startswith('source_review') for p in supervisor.agents.calls))
        admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',f.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error']);self.assertEqual(receipt,current['payload']['candidate_history'][0]['invalid_manifest_attempt']);self.assertEqual(file_hash(receipt['path']),receipt['sha256'])

    def test_info04_successful_provider_quoted_quota_not_a_quota_failure(self):
        supervisor=self.actual_transport('success')
        with patch('school_notes.pipeline.Renderer',f.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('complete',job['state'],job['error']);self.assertFalse(job['payload'].get('quota_block'));self.assertEqual('complete',self.state.rows('SELECT state FROM attempts')[0]['state'])

    def opaque(self,drift=False,sql_failure=False):
        supervisor=self.supervisor()
        class BadBytes(f.FakeAgents):
            def call(inner,job,phase,envelope,cwd,*args,**kwargs):
                response,path=super().call(job,phase,envelope,cwd,*args,**kwargs)
                if phase=='candidate' and not job['payload'].get('candidate_history'):
                    with open(os.fsencode(cwd)+b'/wiki/math/\xff.md','wb') as stream:stream.write(b'preserved non-UTF8 name\n')
                return response,path
        supervisor.agents=BadBytes(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',f.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertIn('unsafe candidate filename',job['error']);old=Path(job['payload']['worktree']);opaque=Path(os.fsdecode(os.fsencode(old)+b'/wiki/math/\xff.md'));sha=file_hash(opaque)
        question=self.state.question(job['id'],'authorization','control','retained control','a'*64);review=self.root/'review.json';atomic_json(review,{'control':True})
        with self.state.db:self.state.db.execute("INSERT INTO reviews(job_id,path,sha256,inputs_hash,scope,state) VALUES (?,?,?,?,?,'accepted')",(job['id'],str(review),file_hash(review),'a'*64,'control'))
        if drift:self.git('config','owner.metadata','controlled-drift')
        if sql_failure:
            with self.state.db:self.state.db.execute("CREATE TRIGGER fail_rebase BEFORE UPDATE ON jobs BEGIN SELECT RAISE(ABORT,'controlled SQL failure'); END")
            before=self.state.job(job['id'])
            with self.assertRaises(sqlite3.IntegrityError):admin.rebase_candidate(supervisor,job['id'])
            self.assertEqual(before,self.state.job(job['id']));self.assertEqual('open',self.state.rows('SELECT state FROM questions WHERE id=?',(question,))[0]['state']);self.assertEqual('accepted',self.state.rows("SELECT state FROM reviews WHERE scope='control'")[0]['state'])
            with self.state.db:self.state.db.execute('DROP TRIGGER fail_rebase')
        admin.rebase_candidate(supervisor,job['id']);retained=self.state.job(job['id'])['payload']['candidate_history'][0];self.assertEqual([{'relative_fs_bytes_hex':b'wiki/math/\xff.md'.hex(),'sha256':sha,'size':len(b'preserved non-UTF8 name\n'),'mode':opaque.stat().st_mode & 0o777}],retained['opaque_files']);self.assertEqual(sha,file_hash(opaque));self.assertEqual('invalidated',self.state.rows("SELECT state FROM reviews WHERE scope='control'")[0]['state']);self.assertEqual('closed',self.state.rows('SELECT state FROM questions WHERE id=?',(question,))[0]['state'])
        with patch('school_notes.pipeline.Renderer',f.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error']);self.assertEqual(sha,file_hash(opaque));self.assertFalse(Path(os.fsdecode(os.fsencode(current['payload']['worktree'])+b'/wiki/math/\xff.md')).exists())

    def test_N1202_actual_post_return_non_utf8_filename_same_ack_retained_and_completes(self):self.opaque()
    def test_N1202_actual_post_return_non_utf8_filename_metadata_drift_retained_and_completes(self):self.opaque(drift=True)
    def test_N1202_failed_atomic_rebase_preserves_review_question_payload(self):self.opaque(sql_failure=True)
