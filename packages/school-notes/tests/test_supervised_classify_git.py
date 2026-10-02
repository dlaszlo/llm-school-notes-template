"""Builder-only regressions for the approved Gitless supervised classify fix."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest

from school_notes.agents import Agent
from school_notes.common import Blocked, private_dir


class SupervisedClassifyGitTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.jobs=private_dir(self.root/'jobs');self.repo=private_dir(self.root/'repo')
        (self.repo/'.git').mkdir()
        self.config=json.loads((Path(__file__).resolve().parents[1]/'config.example.json').read_text())['agents']
        self.config['python']=sys.executable
        self.job={'id':1,'revision_seq':None,'payload':{'worktree':str(self.repo)}}
        self.envelope={'job_id':1,'revision_seq':None,'inputs':[]}

    def build(self,manual,phase='classify',directory=None):
        return Agent(self.config,None,None,None,owner_supervised=manual).build_command(
            self.job,phase,self.envelope,self.repo,directory or self.jobs,'builder fixture',1)

    @staticmethod
    def profile(contract):
        argv=contract['argv'];i=next(i for i,s in enumerate(argv) if s.startswith('permissions.school-notes='))
        return i,tomllib.loads(argv[i])

    def test_only_gitless_manual_classify_exact_deny_removed_config_and_other_argv_unchanged(self):
        configured=copy.deepcopy(self.config);normal=self.build(False);manual=self.build(True)
        i,expected=self.profile(normal);_,actual=self.profile(manual)
        target=str(manual['cwd']/'.git')
        self.assertEqual(expected['permissions']['school-notes']['filesystem'].pop(target),'deny')
        self.assertEqual(actual,expected)
        self.assertEqual(normal['argv'][:i]+normal['argv'][i+1:],manual['argv'][:i]+manual['argv'][i+1:])
        self.assertEqual(normal['environment'],manual['environment']);self.assertEqual(normal['read_dirs'],manual['read_dirs'])
        self.assertEqual(self.config,configured);self.assertFalse((manual['cwd']/'.git').exists())
        self.assertEqual(actual['permissions']['school-notes']['filesystem'][':root'],'deny')
        self.assertFalse(actual['permissions']['school-notes']['network']['enabled'])

    def test_default_classify_keeps_explicit_git_deny(self):
        normal=self.build(False);_,profile=self.profile(normal)
        self.assertEqual(profile['permissions']['school-notes']['filesystem'][str(normal['cwd']/'.git')],'deny')

    def test_manual_candidate_and_reviewer_builders_remain_identical(self):
        for phase in ('candidate','source_review','review'):
            with self.subTest(phase=phase):
                normal=self.build(False,phase);manual=self.build(True,phase)
                self.assertEqual(normal,manual)
                if phase=='candidate':
                    _,profile=self.profile(manual)
                    self.assertEqual(profile['permissions']['school-notes']['filesystem'][str(self.repo/'.git')],'deny')

    def test_separate_learner_repo_git_deny_survives_classify_exception(self):
        i=next(i for i,s in enumerate(self.config['codex']['argv']) if s.startswith('permissions.school-notes='))
        self.config['codex']['argv'][i]=self.config['codex']['argv'][i].replace(',"{cwd}/.git"="deny"',',"{cwd}/.git"="deny",'+json.dumps(str(self.repo/'.git'))+'="deny"')
        manual=self.build(True);_,profile=self.profile(manual)
        filesystem=profile['permissions']['school-notes']['filesystem']
        self.assertNotIn(str(manual['cwd']/'.git'),filesystem)
        self.assertEqual(filesystem[str(self.repo/'.git')],'deny')

    def test_unforeseen_git_file_directory_or_broken_link_refuses_before_returning_argv(self):
        for kind in ('file','directory','broken-link'):
            with self.subTest(kind=kind):
                directory=private_dir(self.root/kind);workspace=directory
                for child in ('private-classify','attempt-1-classify','workspace'):workspace=private_dir(workspace/child)
                path=workspace/'.git'
                if kind=='file':path.write_text('unexpected Git file')
                elif kind=='directory':path.mkdir()
                else:path.symlink_to(workspace/'missing')
                with self.assertRaisesRegex(Blocked,'unexpected Git metadata'):self.build(True,directory=directory)
                self.assertTrue(path.is_symlink() or path.exists())

    def test_ancestor_alias_workspace_cannot_take_gitless_exception(self):
        alias=self.root/'alias';alias.symlink_to(self.jobs,target_is_directory=True)
        with self.assertRaisesRegex(Blocked,'must be canonical'):self.build(True,directory=alias)

    def test_unknown_or_non_deny_profile_shape_fails_closed_without_config_mutation(self):
        i=next(i for i,s in enumerate(self.config['codex']['argv']) if s.startswith('permissions.school-notes='))
        original=self.config['codex']['argv'][i]
        for replacement in (',"{cwd}/.git"="write"',',"{cwd}/.git" = "deny"',''):
            with self.subTest(replacement=replacement):
                self.config['codex']['argv'][i]=original.replace(',"{cwd}/.git"="deny"',replacement)
                configured=copy.deepcopy(self.config)
                with self.assertRaisesRegex(Blocked,'omit only'):self.build(True)
                self.assertEqual(self.config,configured)


if __name__=='__main__':unittest.main()
