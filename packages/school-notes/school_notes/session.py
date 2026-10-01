"""Cooperative owner sessions. Membership is process ancestry, never authorization.

Same-UID callers can deliberately circumvent cooperation; this is not a security
boundary. Native tool environment/namespace behavior requires its own proof.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import uuid

from .common import Blocked, Busy, RunLock, atomic_json, digest, file_hash, now, private_dir, terminate_group
from .state import State
from .verify import Git

ENV='SCHOOL_NOTES_SESSION'
AUTHORIZATION={'approve-public','approve-subject','approve-attempts','clear-quota','acknowledge-baseline','acknowledge-maintenance','link-baseline','resolve-effect','close-job','reject-package'}


def paths(config):
    return Path(config['lock_file']+'.session'),Path(config['lock_file']+'.session.json')


def process_identity(pid):
    try:
        path=Path(f'/proc/{pid}')
        fields=(path/'stat').read_text().split(') ',1)[1].split()
        return {'pid':int(pid),'start_ticks':fields[19],'uid':path.stat().st_uid,'ppid':int(fields[1]),'state':fields[0]}
    except (OSError,ValueError,IndexError):return None


def same_process(value):
    if not value:return False
    actual=process_identity(value['pid'])
    return actual is not None and actual['state']!='Z' and all(actual.get(k)==value.get(k) for k in ('pid','start_ticks','uid'))


def marker(config):
    path=paths(config)[1]
    if not path.exists():return None
    if path.is_symlink() or path.stat().st_uid!=os.getuid() or path.stat().st_mode & 0o077:raise Blocked('unsafe session marker; owner recovery required')
    value=json.loads(path.read_text())
    if not isinstance(value,dict):raise Blocked('invalid session marker')
    return value


def active(value):
    return value and value.get('state') in ('starting','running','closing','recovery-required')


def verify(config,config_path=None):
    supplied=os.environ.get(ENV)
    if supplied is None:return None
    guard,pointer=paths(config)
    if Path(supplied)!=pointer:raise Blocked('session pointer mismatch; no joined operation')
    value=marker(config)
    if not value or value.get('state')!='running' or value.get('config_hash')!=digest(config):raise Blocked('stale/config-changed session identity; no joined operation')
    if config_path is not None and value.get('config_path') and str(Path(config_path).resolve())!=value['config_path']:raise Blocked('session canonical config path mismatch')
    if not same_process(value['wrapper']) or not same_process(value['command']) or value['wrapper']['uid']!=os.getuid():raise Blocked('stale session process identity')
    current=os.getpid();found=False
    for _ in range(256):
        identity=process_identity(current)
        if identity is None or identity['uid']!=os.getuid():break
        if current==value['command']['pid']:
            found=identity['start_ticks']==value['command']['start_ticks'];break
        if identity['ppid'] in (0,current):break
        current=identity['ppid']
    if not found:raise Blocked('caller is not the recorded foreground session descendant; namespace/env unsupported')
    stat=guard.stat()
    if [stat.st_dev,stat.st_ino]!=value['guard_inode']:raise Blocked('session guard inode changed')
    held=False
    for fd in Path(f"/proc/{value['wrapper']['pid']}/fd").iterdir():
        try:
            item=fd.stat()
            held |= (item.st_dev,item.st_ino)==(stat.st_dev,stat.st_ino)
        except OSError:continue
    if not held:raise Blocked('wrapper does not hold recorded session guard')
    probe=os.open(guard,os.O_RDWR|os.O_NOFOLLOW)
    try:
        try:fcntl.flock(probe,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:pass
        else:raise Blocked('recorded exclusive session guard is not held')
    finally:os.close(probe) # never change the inherited open-file description
    return value


class Admission:
    """Acquire session participation before a fresh exclusive operation lock."""
    def __init__(self,config,config_path=None):self.config=config;self.config_path=config_path;self.fd=None;self.session=None
    def __enter__(self):
        self.session=verify(self.config,self.config_path)
        if self.session:return self
        guard,_=paths(self.config);private_dir(guard.parent)
        self.fd=os.open(guard,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:fcntl.flock(self.fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(self.fd);self.fd=None
            raise Busy('scheduled processing paused by protected owner session') from None
        try:
            if active(marker(self.config)):raise Busy('retained session marker requires explicit recover; no age-based unlock')
        except BaseException:self.__exit__();raise
        return self
    def recheck(self):
        if self.session:self.session=verify(self.config,self.config_path)
        elif active(marker(self.config)):raise Busy('owner session changed while acquiring operation lock')
    def __exit__(self,*_):
        if self.fd is not None:os.close(self.fd);self.fd=None


def lock_holders(path):
    try:target=Path(path).stat()
    except FileNotFoundError:return []
    result=[]
    for process in Path('/proc').glob('[0-9]*'):
        try:
            if process.stat().st_uid!=os.getuid():continue
            for fd in (process/'fd').iterdir():
                try:item=fd.stat()
                except OSError:continue
                if (item.st_dev,item.st_ino)==(target.st_dev,target.st_ino):
                    identity=process_identity(int(process.name))
                    if identity:result.append(identity)
                    break
        except OSError:continue
    return result


def diagnostics(config):
    value=marker(config)
    return {'session':value,'operation_lock_holders':lock_holders(config['lock_file']),'scheduled_processing':f"paused: protected owner session {value.get('learner','unknown')} since {value.get('started','unknown')} ({value.get('state')})" if active(value) else 'available',
            'native_session_proof':'not inferred from synthetic process tests'}


def recover(config):
    guard,pointer=paths(config);private_dir(guard.parent)
    fd=os.open(guard,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise Busy('live session/child still holds guard; no forced unlock') from None
        value=marker(config)
        if active(value):
            item=os.fstat(fd)
            if [item.st_dev,item.st_ino]!=value.get('guard_inode'):raise Blocked('recorded session guard inode changed; explicit owner maintenance required')
            if any(same_process(value[key]) for key in ('wrapper','command') if value.get(key)):
                raise Busy('recorded owner process still lives; finish it before recovery')
            with RunLock(config['lock_file']):
                value.update(state='recovered',recovered=now(),recovery='all recorded process identities gone; both locks acquired; no file deleted')
                atomic_json(pointer,value)
        return value
    finally:os.close(fd)


def default_command(config):
    prefix=config.get('interactive_command')
    if not isinstance(prefix,list) or not prefix or not all(isinstance(x,str) and '\0' not in x for x in prefix) or not Path(prefix[0]).is_absolute() or not Path(prefix[0]).is_file():
        raise Blocked('interactive needs configured absolute interactive_command launcher or explicit trusted argv after --')
    return prefix+['--no-daemon','--model','gpt-6.1-sol','-c','model_reasoning_effort="high"']


def inventory(git,base):
    from .admin import ordinary_snapshot
    ordinary,opaque=ordinary_snapshot(git.repo)
    # Only changed/untracked names for ordinary receipt, never copy bytes.
    names=set(git.diff_names(base,timeout=10)+git.names('ls-files','--others','--exclude-standard','-z',timeout=10))
    return {n:ordinary.get(n) for n in sorted(names) if not any(0xD800<=ord(c)<=0xDFFF for c in n)},opaque


def wrapper(config,learner,argv,*,config_path=None):
    if learner not in config['learners']:raise Blocked('unknown learner')
    if os.environ.get(ENV):raise Blocked('nested owner session is unsupported')
    if argv and argv[0]=='--':argv=argv[1:]
    pinned=not argv
    argv=argv or default_command(config)
    controller=None
    if config_path is not None:
        import shlex
        controller='UV_OFFLINE=1 PYTHONPATH='+shlex.quote(str(Path(__file__).parents[1]))+' '+shlex.join([sys.executable,'-B','-m','school_notes','--config',str(Path(config_path).resolve())])
        if pinned:
            argv=argv+['Trusted owner School Notes session for '+learner+'. Normal operations use the existing deterministic controller: '+controller+'. Use status/inspect-job for diagnosis, sync for observation only, run-once --job JOB_ID for finite processing/review, answer QUESTION_ID FILE then run-once, resume or rebase-candidate for preserved continuation, build-preview '+learner+' for an unreviewed private preview, and finalize-external JOB_ID after accepted external review. Authorization verbs require explicit owner action outside this session. Run controller calls sequentially, using the already-authorized execution outside the tool sandbox; never install permission rules or use bypass flags. Direct edits are protected while this foreground session lives. This session and its requested model configuration are not proof or accepted review.']
    if not all(isinstance(x,str) and '\0' not in x for x in argv):raise Blocked('invalid trusted interactive argv')
    grace=config.get('interactive_terminate_grace_seconds',2)
    if isinstance(grace,bool) or not isinstance(grace,(int,float)) or not 0.05<=grace<=10:raise Blocked('interactive termination grace must be finite, 0.05..10 seconds')
    guard,pointer=paths(config);private_dir(guard.parent)
    fd=os.open(guard,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    process=None;terminal=None;original_group=None;previous_handler=None;receipt=None;directory=None;git=None;errors=[]
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise Busy('another operation/session holds session participation') from None
        previous=marker(config)
        if active(previous):raise Busy('previous session requires recover; no silent marker replacement')
        with RunLock(config['lock_file']) as lock:
            state=State(config['state_db'])
            try:
                baseline=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f'baseline:{learner}',))
                if not baseline or not baseline[0]['ack_sha']:raise Blocked('interactive requires acknowledged baseline')
                git=Git(config['learners'][learner]['repo'],lock);start=git.head(timeout=10)
                hashes,opaque=inventory(git,baseline[0]['ack_sha'])
            finally:state.close()
        directory=private_dir(Path(config['jobs_dir'])/('interactive-'+str(uuid.uuid4())))
        stat=os.fstat(fd)
        receipt={'learner':learner,'started':now(),'state':'starting','review':False,'origin':'trusted-owner-session','config_hash':digest(config),'wrapper':process_identity(os.getpid()),'command':None,'guard_inode':[stat.st_dev,stat.st_ino],
                 'config_path':str(Path(config_path).resolve()) if config_path is not None else None,'controller_command':controller,'start_commit':start,'entry_ack':baseline[0]['ack_sha'],'start_hashes':hashes,'start_opaque_files':opaque,'previous_session':{'receipt':previous.get('receipt'),'sha256':file_hash(previous['receipt']) if previous and previous.get('receipt') and Path(previous['receipt']).is_file() else None} if previous else None,'argv':argv,'pinned_default':pinned,'native_proof':'unverified','receipt':str(directory/'receipt.json')}
        atomic_json(pointer,receipt)
        readfd,writefd=os.pipe();env=dict(os.environ);env[ENV]=str(pointer)
        previous_handler=signal.signal(signal.SIGTTOU,signal.SIG_IGN)
        try:
            terminal=os.open('/dev/tty',os.O_RDWR);original_group=os.tcgetpgrp(terminal)
        except OSError:
            if terminal is not None:os.close(terminal)
            terminal=None
        try:
            process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('_session_child.py')),str(readfd),*argv],cwd=git.repo,env=env,pass_fds=(fd,readfd),process_group=0)
            os.close(readfd);receipt.update(command=process_identity(process.pid),state='running');atomic_json(pointer,receipt)
            if terminal is not None:os.tcsetpgrp(terminal,process.pid)
            os.write(writefd,b'1')
        finally:os.close(writefd)
        receipt['exit_code']=process.wait() # owner lifetime is never the scheduled window
    finally:
        if receipt is not None:
            def cleanup(label,action):
                try:action()
                except Exception as error:errors.append({'phase':label,'type':type(error).__name__,'error':str(error)})
            receipt['state']='closing';cleanup('closing-marker',lambda:atomic_json(pointer,receipt))
            if process is not None:
                cleanup('terminate-group',lambda:terminate_group(process.pid,grace=grace))
                cleanup('wait-child',lambda:process.wait(timeout=grace+1))
                receipt.setdefault('exit_code',process.returncode)
            if terminal is not None:
                cleanup('restore-terminal',lambda:os.tcsetpgrp(terminal,original_group));cleanup('close-terminal',lambda:os.close(terminal))
            if previous_handler is not None:cleanup('restore-signal',lambda:signal.signal(signal.SIGTTOU,previous_handler))
            receipt.update(finished=now(),state='recorded' if not errors else 'recovery-required',cleanup_errors=errors,inspection_errors=[])
            try:
                with RunLock(config['lock_file']) as lock:
                    owner=Git(config['learners'][learner]['repo'],lock)
                    receipt['metadata_drift']={'start':git.identity,'end':owner.identity} if owner.identity!=git.identity else None
                    state=State(config['state_db'])
                    try:
                        base=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f'baseline:{learner}',))[0]['ack_sha']
                        end=owner.head(timeout=10);hashes,opaque=inventory(owner,base)
                        receipt.update(review_base=base,end_commit=end,hashes=hashes,opaque_files=opaque)
                        clean=not owner.git('status','--porcelain','--untracked-files=all',timeout=10)
                        pushed=end==owner.git('rev-parse','refs/remotes/origin/main',timeout=10)
                        ancestor=base in owner.git('rev-list',end,timeout=10).splitlines()
                        receipt['range_state']='ancestor' if ancestor else 'diverged from acknowledgement; owner must assess possible history rewrite and current remote before explicit checkout reconciliation/maintenance'
                        atomic_json(directory/'receipt.json',receipt) # immutable before job links
                        from .pipeline import register_external
                        job=register_external(state,owner,learner,base,end,ready=clean and pushed and ancestor and not opaque and not errors,provenance={'wrapper_receipt':str(directory/'receipt.json'),'receipt_hash':file_hash(directory/'receipt.json')}) if ancestor and end!=base and not opaque else None
                        atomic_json(directory/'registration.json',{'receipt_sha256':file_hash(directory/'receipt.json'),'job_id':job,'provisional':not clean or not pushed,'review':False})
                    finally:state.close()
            except Exception as error:
                receipt['inspection_errors'].append({'phase':'fresh-owner-git','type':type(error).__name__,'error':str(error)})
                # No job could bind this path until immutable receipt was written.
                if not (directory/'receipt.json').exists():atomic_json(directory/'receipt.json',receipt)
                atomic_json(directory/'cleanup.json',{'errors':receipt['inspection_errors'],'receipt_sha256':file_hash(directory/'receipt.json')})
            if errors or receipt['inspection_errors']:receipt['state']='recovery-required'
            atomic_json(pointer,receipt)
        os.close(fd)
    return receipt
