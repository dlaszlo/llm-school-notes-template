"""Independent finite worker guardian with process-local descendant ownership."""
import ctypes
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def identity(pid):
    try:
        path=Path(f'/proc/{pid}');fields=(path/'stat').read_text().split(') ',1)[1].split()
        return (fields[19],int(fields[1]),path.stat().st_uid,fields[0])
    except (OSError,IndexError,ValueError):return None


def descendants(owned):
    # The subreaper owns reparented worker descendants, including new groups.
    # Never infer ownership from UID or a recycled PID alone.
    processes={int(path.name):identity(int(path.name)) for path in Path('/proc').glob('[0-9]*')}
    parents={os.getpid()}
    while True:
        found={pid for pid,value in processes.items() if value and value[1] in parents and value[2]==os.getuid() and pid not in parents}
        if not found:break
        parents.update(found)
    for pid in parents-{os.getpid()}:
        value=processes[pid]
        owned[pid]=value[0]
    return {pid for pid,start in owned.items() if (value:=identity(pid)) and value[0]==start and value[2]==os.getuid() and value[3]!='Z'}


def main():
    parent=int(sys.argv[1]);parent_start=sys.argv[2];deadline=float(sys.argv[3]);fds=tuple(int(x) for x in sys.argv[4].split(',') if x)
    # Linux process-local setting; no permissions, cgroup or host config change.
    if ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0)!=0:
        raise OSError(ctypes.get_errno(),'worker subreaper unavailable; no child started')
    stopped=False
    def stop(*_):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    actual=identity(parent)
    if time.monotonic()>=deadline:return 124
    if stopped or not actual or actual[0]!=parent_start:return 125
    child=subprocess.Popen(sys.argv[5:],start_new_session=True,pass_fds=fds)
    owned={};expired=False
    try:
        while child.poll() is None:
            descendants(owned)
            expired=time.monotonic()>=deadline
            actual=identity(parent)
            if stopped or expired or not actual or actual[0]!=parent_start:break
            time.sleep(.02)
        code=child.poll()
    finally:
        live=descendants(owned)
        for pid in live:
            try:os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:pass
        if live:time.sleep(.05)
        cleanup_deadline=time.monotonic()+2
        while True:
            live=descendants(owned)
            for pid in live:
                try:os.kill(pid,signal.SIGKILL)
                except ProcessLookupError:pass
            child.poll()
            # Reap adopted children only after Popen has observed its own child.
            if child.returncode is not None:
                while True:
                    try:
                        pid,_=os.waitpid(-1,os.WNOHANG)
                        if not pid:break
                    except ChildProcessError:break
            if not live:break
            if time.monotonic()>cleanup_deadline:
                raise RuntimeError('owned worker descendants did not stop; operation FD remains held by surviving child')
            time.sleep(.01)
        child.wait()
    return 124 if expired else (code if code is not None and code>=0 else 125)


if __name__=='__main__':sys.exit(main())
