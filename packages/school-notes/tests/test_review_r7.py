"""R7 constructor interruption and owner-source maintenance recovery gates."""
import http.client,json
from pathlib import Path
from unittest.mock import patch
import test_app as fixture
import test_review_r2 as r2
from school_notes import admin
from school_notes.common import Blocked,atomic_json,file_hash
from school_notes.drive import DriveAPI,ReadOnlyDriveAPI
from school_notes.verify import Git

class R7Tests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor
    evidence_records=r2.R2Tests.evidence_records

    def test_N701_constructor_refresh_interruption_writer_and_reader_bounded(self):
        helper=self.root/'controlled-helper.py';helper.write_text('import http.client\nclass Refused(Exception):pass\nclass Drive:\n def __init__(self,path):raise http.client.IncompleteRead(b"controlled",5)\n')
        proof={k:True for k in ('manual_upload_read','recursive_visibility','child_account_access','token_refresh','oauth_project_status_checked')};path=self.root/'synthetic-writer.json';atomic_json(path,proof)
        with self.assertRaisesRegex(Blocked,'token refresh interrupted'):DriveAPI(helper,self.root,path)
        proof.update(scope='https://www.googleapis.com/auth/drive.readonly',config_dir=str(self.root.resolve()),readonly_only=True);atomic_json(path,proof)
        with self.assertRaisesRegex(Blocked,'token refresh interrupted'):ReadOnlyDriveAPI(helper,self.root,path)

    def policy_setup(self,policy):
        (self.repo/'.gitattributes').write_text(policy);self.git('add','.');self.git('commit','-m','Owner source policy');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        return head

    def maintenance(self,supervisor,policy):
        (self.repo/'.gitattributes').write_text(policy);self.git('add','.');self.git('commit','-m','Owner preserve original source bytes');self.git('push','origin','HEAD:main');supervisor.observe_git('student');job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review' ORDER BY id DESC")[0]['id']);manifest=json.loads((self.repo/'publication/pilot.json').read_text());head=self.git('rev-parse','HEAD')
        evidence={'job_id':job['id'],'base':job['payload']['base'],'head':head,'changes':job['payload']['changes'],'open_reviews':[],'open_questions':[],'reason':'Owner exact source policy maintenance, no original rewrite','closure_records':self.evidence_records(),'manifest_impact':{'path':'publication/pilot.json','sha256':file_hash(self.repo/'publication/pilot.json'),'manifest':manifest}}
        admin.acknowledge_maintenance(supervisor,job['id'],evidence)

    def test_N702_owner_filter_same_ack_refuses_no_budget_then_maintenance_completes(self):
        self.policy_setup('sources/** filter=owner-filter\n');supervisor=self.supervisor()
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);old=Path(job['payload']['worktree']);original={str(p.relative_to(old)):file_hash(p) for p in (old/'sources').rglob('*') if p.is_file()};payload_before=job['payload'];dirs=list(supervisor.job_dir(job).glob('worktree*'))
        self.git('config','owner.metadata','changed-after-source-policy-block')
        for _ in range(3):
            with self.assertRaisesRegex(Blocked,'acknowledge-maintenance'):admin.rebase_candidate(supervisor,job['id'])
            self.assertEqual(payload_before,self.state.job(job['id'])['payload']);self.assertEqual(dirs,list(supervisor.job_dir(job).glob('worktree*')))
        self.maintenance(supervisor,'sources/** -filter -working-tree-encoding -text\n');admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error']);self.assertEqual(1,len(current['payload']['candidate_history']));self.assertEqual(original,{str(p.relative_to(old)):file_hash(p) for p in (old/'sources').rglob('*') if p.is_file()})

    def test_N707_source_normalization_owner_policy_never_suggests_rewrite(self):
        from school_notes.verify import OwnerPolicyViolation
        self.policy_setup('* text=auto eol=lf\n');git=Git(self.repo);source=self.repo/'sources/text-like.pdf';source.write_bytes(b'%PDF-1.4\r\ntext-like exact original\r\n');before=source.read_bytes()
        with self.assertRaises(OwnerPolicyViolation) as caught:git.changes(git.head(),sources=[{'path':str(source),'sha256':file_hash(source)}])
        self.assertIn('acknowledge-maintenance',str(caught.exception));self.assertNotIn('write LF',str(caught.exception));self.assertEqual(before,source.read_bytes())
        policy=self.repo/'.gitattributes';policy.write_text('sources/** -text\n');self.git('add','.gitattributes');self.git('commit','-m','Owner exact-source policy');self.assertIn('sources/text-like.pdf',Git(self.repo).changes(self.git('rev-parse','HEAD'),sources=[{'path':str(source),'sha256':file_hash(source)}]));self.assertEqual(before,source.read_bytes())

    def test_N702_inherited_attributes_owner_error_agent_policy_write_candidate_error(self):
        from school_notes.verify import OwnerPolicyViolation,CandidateViolation
        self.policy_setup('sources/** working-tree-encoding=UTF-16\n');git=Git(self.repo)
        with self.assertRaises(OwnerPolicyViolation):git.source_attributes('sources/new.png')
        (self.repo/'.gitattributes').write_text('agent changed protected owner policy\n')
        with self.assertRaises(CandidateViolation):git.changes(git.head())
