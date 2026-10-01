"""R11 actual finite adapter manifest failures and unsafe-name preservation."""
import copy,json,sys
from pathlib import Path
from unittest.mock import patch
import test_app as fixture
import test_review_r2 as r2
from school_notes import admin
from school_notes.agents import Agent,validate_result
from school_notes.common import Blocked,Window,atomic_json,file_hash
from school_notes.verify import CandidateViolation,Git

class R11Tests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor

    def malformed(self,kind):
        if kind=='mutate_evidence':
            (self.repo/'AGENTS.md').write_text('Trusted owner learner rules\n');self.git('add','.');self.git('commit','-m','Owner trusted rules');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
            with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor();config=json.loads((fixture.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable
        agent=Agent(config,self.state,supervisor.lock,Window());proof=self.root/'synthetic-only.json';atomic_json(proof,{'synthetic_transport_only':True});settings=agent.role_settings('codex');settings.update(evidence=str(proof),timeout=30,argv=[sys.executable,'-c','pass'])
        class Transport(fixture.FakeAgents):
            def call(inner,job,phase,envelope,cwd,directory,instructions):
                if phase!='candidate':return super().call(job,phase,envelope,cwd,directory,instructions)
                def provider(argv,execution_cwd,**kwargs):
                    response,_=super(Transport,inner).call(job,phase,envelope,cwd,directory,instructions)
                    proposal=response['manifest_proposal']
                    if not job['payload'].get('candidate_history'):
                        if kind=='schema':proposal['pages'].append({'path':'wiki/math/lesson.md','title':'Unsupported'})
                        raw=json.dumps(proposal) if kind=='schema' else '{"pages":'
                    else:raw=json.dumps(proposal)
                    if kind=='input_hash':response['input_hash']='wrong'
                    if kind=='context':response['source_context']={'purpose':'invalid'}
                    if kind=='mutate_evidence':Path(envelope['trusted_policy'][0]['path']).write_text('mutated bound learner policy')
                    response['manifest_proposal']=raw;attempt=Path(kwargs['log']).parent;atomic_json(attempt/'result.json',response);(attempt/'events.log').write_text('{"type":"turn.completed"}\n')
                with patch.object(agent,'_gate',return_value=settings),patch('school_notes.agents.run',provider):
                    return agent.call(job,phase,envelope,cwd,directory,instructions)
        supervisor.agents=Transport(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertEqual('candidate',job['phase']);self.assertFalse(any(p.startswith('source_review') for p in supervisor.agents.calls))
        if kind not in ('schema','json'):
            expected={'input_hash':'agent job/revision/input hash mismatch','context':'invalid sanitized educational/source context','mutate_evidence':'agent changed its bound input evidence'}
            self.assertIn(expected[kind],job['error'])
            self.assertNotIn('agent_manifest_proposal',job['payload']);self.assertNotIn('invalid_manifest_attempt',job['payload'])
            return
        self.assertIn('agent_manifest_proposal',job['payload']);self.assertIsInstance(job['payload']['agent_manifest_proposal'],str)
        receipt=Path(job['payload']['candidate_result']);sha=file_hash(receipt);attempts=self.state.rows('SELECT * FROM attempts WHERE job_id=?',(job['id'],));self.assertEqual(1,len(attempts));self.assertEqual('failed',attempts[0]['state']);self.assertEqual(sha,attempts[0]['result_hash']);old=Path(job['payload']['worktree'])
        admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error']);self.assertEqual(sha,file_hash(receipt));self.assertTrue(old.exists());self.assertEqual(job['payload']['invalid_manifest_attempt'],current['payload']['candidate_history'][0]['invalid_manifest_attempt']);self.assertNotIn('attempt_exceptions',current['payload']);attempts=self.state.rows('SELECT * FROM attempts WHERE job_id=? ORDER BY id',(job['id'],));self.assertEqual(['failed','complete'],[a['state'] for a in attempts]);self.assertNotEqual(attempts[0]['phase'],attempts[1]['phase'])

    def test_N1101_unknown_page_field_actual_call_failed_receipt_and_rebase(self):self.malformed('schema')
    def test_N1101_malformed_manifest_json_actual_call_failed_receipt_and_rebase(self):self.malformed('json')
    def test_N1101_wrong_envelope_actual_call_no_proposal_recovery(self):self.malformed('input_hash')
    def test_N1101_wrong_context_actual_call_no_proposal_recovery(self):self.malformed('context')
    def test_N1101_mutated_bound_policy_actual_call_no_proposal_recovery(self):self.malformed('mutate_evidence')

    def unsafe(self,owner=False):
        if owner:
            (self.repo/'.gitattributes').write_text('wiki/** filter=owner-filter\n');self.git('add','.');self.git('commit','-m','Owner wiki filter');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
            with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor();name='wiki/math/agent\\unsafe.md'
        class BadName(fixture.FakeAgents):
            def call(inner,job,phase,envelope,cwd,*args,**kwargs):
                if phase=='candidate' and not job['payload'].get('candidate_history'):(Path(cwd)/name).write_bytes(b'preserved unsafe name\n')
                return super().call(job,phase,envelope,cwd,*args,**kwargs)
        supervisor.agents=BadName(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);old=Path(job['payload']['worktree']);sha=file_hash(old/name)
        if owner:
            self.assertIn('owner_policy_failure',job['payload']);(self.repo/'.git/info/attributes').write_text('wiki/** -filter\n');self.git('config','owner.metadata','owner-repair-name-drift')
        else:self.assertIn('unsafe candidate filename',job['error'])
        admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error']);self.assertEqual(sha,file_hash(old/name));self.assertEqual(sha,current['payload']['candidate_history'][0]['changes'][name]);self.assertFalse((Path(current['payload']['worktree'])/name).exists())

    def test_N1102_new_backslash_name_same_ack_snapshot_and_complete(self):self.unsafe()
    def test_N1102_owner_preflight_quarantines_only_new_unsafe_name(self):self.unsafe(True)

    def test_N1102_inherited_unsafe_name_stays_owner_maintenance(self):
        path=self.repo/'wiki/math/owner\\unsafe.md';path.write_text('Owner baseline bytes\n');self.git('add','.');self.git('commit','-m','Owner inherited unsafe filename');git=Git(self.repo);base=git.head()
        for operation in (lambda:git.changes(base),lambda:git.ordinary_changed_paths(self.repo,base)):
            with self.assertRaisesRegex(Blocked,'owner maintenance') as caught:operation()
            self.assertNotIsInstance(caught.exception,CandidateViolation)
        self.assertEqual('Owner baseline bytes\n',path.read_text())

    def test_N1101_other_invalid_fields_not_manifest_repair(self):
        envelope={'job_id':1,'revision_seq':1,'inputs':[]}
        for field,value in (('input_hash','wrong'),('review',{'content':'bad'}),('source_context',{'purpose':'invalid'})):
            response=fixture.result(envelope);response['manifest_proposal']='{"pages":';response[field]=value
            with self.assertRaises(Blocked) as caught:validate_result(response,envelope)
            self.assertEqual('Blocked',type(caught.exception).__name__)
