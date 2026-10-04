"""Durable endpoint backpressure for cooperating collectors on one POSIX host.

The existing NativeReadGate is extended, never replaced as an authority owner.
Slot locks live through socket cleanup and kernel locks release on process exit.
The rate reservation is flushed before read admission and survives restart.
Independent hosts/directories, filesystems without POSIX flock/fsync guarantees,
state restore, native fencing and credential issuance are outside this contract.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
import hashlib
import math
import os
from pathlib import Path
import secrets
import stat
import time
from typing import Callable

from .collector_settings import protected_path
from .model import _json, _utc
from .native_credentials import decode_json
from .read_budget import EndpointReadPolicy, NativeReadAdmissionHeld, NativeReadGate
from .review_files import private_parent, publish_once, read_private
from .trust import _keys


class SharedNativeReadGate(NativeReadGate):
    """One immutable endpoint policy shared across batches/tenants on this host."""

    def __init__(self, policy: EndpointReadPolicy, *, directory, stopped=None,
                 clock: Callable[[], datetime] = lambda:datetime.now(timezone.utc)):
        super().__init__(policy, stopped=stopped)
        self.directory = protected_path(str(directory))
        if not callable(clock):raise TypeError('Current trusted UTC clock is required')
        self._clock = clock
        self._key = hashlib.sha256(_json(list(policy.key)).encode('ascii')).hexdigest()
        self._policy = {'format':'hosting-discovery-shared-read-policy/1',
                        **asdict(policy)}
        self._digest = hashlib.sha256(_json(self._policy).encode('ascii')).hexdigest()
        self._directory_identity = None
        self._lock_identity = None
        self._slot_identities = {}
        self._enroll()

    def _path(self, suffix):return str(self.directory/(self._key+suffix))

    def _open_lock(self, parent, suffix):
        import fcntl
        name=self._key+suffix
        fd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,0o600,dir_fd=parent)
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid()
                or info.st_mode&0o077 or info.st_nlink!=1 or info.st_size!=0):
            os.close(fd)
            raise NativeReadAdmissionHeld('Shared budget lock is not a private empty regular file')
        return fd

    def _enroll(self):
        import fcntl
        with private_parent(self._path('.lock')) as (parent,_):
            info=os.fstat(parent)
            if info.st_uid!=os.geteuid():raise NativeReadAdmissionHeld('Budget state is not owned by this service')
            self._directory_identity=(info.st_dev,info.st_ino)
            fd=self._open_lock(parent,'.lock')
            try:
                # Enrollment is bounded and happens before any native contact.
                end=time.monotonic()+5
                while True:
                    self.check()
                    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                    except BlockingIOError:
                        if time.monotonic()>=end:raise NativeReadAdmissionHeld('Budget enrollment lock is held')
                        self._stopped.wait(.05)
                linked=os.stat(self._key+'.lock',dir_fd=parent,follow_symlinks=False)
                self._lock_identity=(linked.st_dev,linked.st_ino)
                path=self._path('.policy.json')
                created=False
                try:raw=read_private(path,2048)
                except FileNotFoundError:
                    # A missing policy with existing rate/slot state cannot reset limits.
                    if any(name.startswith(self._key) and name!=self._key+'.lock' for name in os.listdir(parent)):
                        raise NativeReadAdmissionHeld('Existing endpoint budget requires policy reconciliation')
                    raw=_json(self._policy).encode('ascii')
                    publish_once(path,raw,self.check)
                    created=True
                if raw!=_json(self._policy).encode('ascii'):
                    raise NativeReadAdmissionHeld('Endpoint budget policy differs from its enrollment')
                for index in range(self.policy.max_concurrent):
                    suffix=f'.slot-{index:02d}.lock'
                    slot=self._open_lock(parent,suffix)
                    info=os.fstat(slot);os.close(slot)
                    self._slot_identities[suffix]=(info.st_dev,info.st_ino)
                identities={'format':'hosting-discovery-shared-read-identity/1',
                    'policyDigest':self._digest,'directory':list(self._directory_identity),
                    'lock':list(self._lock_identity),
                    'slots':{key:list(value) for key,value in self._slot_identities.items()}}
                if created:
                    publish_once(self._path('.identity.json'),_json(identities).encode('ascii'),self.check)
                    self._reserve(parent,datetime(1970,1,1,tzinfo=timezone.utc))
                elif read_private(self._path('.identity.json'),4096)!=_json(identities).encode('ascii'):
                    raise NativeReadAdmissionHeld('Endpoint budget lock identities changed')
                # Absence after enrollment is a loss of reservation custody, not an unused slot.
                if self._rate() is None:raise NativeReadAdmissionHeld('Endpoint rate reservation is missing')
                os.fsync(parent)
            finally:os.close(fd)

    def check(self):
        super().check()
        if self._directory_identity is None:return
        with private_parent(self._path('.lock')) as (parent,name):
            info=os.fstat(parent)
            lock=os.stat(name,dir_fd=parent,follow_symlinks=False)
            if ((info.st_dev,info.st_ino)!=self._directory_identity or info.st_uid!=os.geteuid()
                    or self._lock_identity is not None and (lock.st_dev,lock.st_ino)!=self._lock_identity
                    or not stat.S_ISREG(lock.st_mode) or lock.st_nlink!=1 or lock.st_mode&0o077):
                raise NativeReadAdmissionHeld('Shared endpoint budget identity changed')
            for suffix,identity in self._slot_identities.items():
                value=os.stat(self._key+suffix,dir_fd=parent,follow_symlinks=False)
                if ((value.st_dev,value.st_ino)!=identity or not stat.S_ISREG(value.st_mode)
                        or value.st_uid!=os.geteuid() or value.st_mode&0o077 or value.st_nlink!=1):
                    raise NativeReadAdmissionHeld('Shared endpoint slot identity changed')

    def _rate(self):
        try:raw=read_private(self._path('.rate.json'),2048)
        except FileNotFoundError:return None
        doc=_keys(decode_json(raw,2048),{'format','policyDigest','lastStartedAt','notBefore','recordDigest'})
        body={k:v for k,v in doc.items() if k!='recordDigest'}
        if (doc['format']!='hosting-discovery-shared-read-reservation/1' or doc['policyDigest']!=self._digest
                or raw!=_json(doc).encode('ascii')
                or hashlib.sha256(_json(body).encode('ascii')).hexdigest()!=doc['recordDigest']):
            raise NativeReadAdmissionHeld('Shared endpoint rate reservation changed')
        start,end=(datetime.fromisoformat(doc[k]) for k in ('lastStartedAt','notBefore'))
        if (not _utc(start) or not _utc(end)
                or end-start!=timedelta(milliseconds=self.policy.min_interval_ms)):
            raise NativeReadAdmissionHeld('Invalid shared endpoint rate reservation')
        return start,end

    def _reserve(self,parent,at):
        body={'format':'hosting-discovery-shared-read-reservation/1','policyDigest':self._digest,
              'lastStartedAt':at.isoformat(),
              'notBefore':(at+timedelta(milliseconds=self.policy.min_interval_ms)).isoformat()}
        body['recordDigest']=hashlib.sha256(_json(body).encode('ascii')).hexdigest()
        raw=_json(body).encode('ascii')
        name=self._key+'.rate.json';temporary='.budget-'+secrets.token_hex(16)
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=parent)
        try:
            with os.fdopen(fd,'wb',closefd=False) as stream:
                stream.write(raw);stream.flush();os.fsync(fd)
            self.check()
            os.replace(temporary,name,src_dir_fd=parent,dst_dir_fd=parent)
            os.fsync(parent)
        finally:
            os.close(fd)
            try:os.unlink(temporary,dir_fd=parent)
            except FileNotFoundError:pass

    @contextmanager
    def permit(self,deadline,authorize):
        import fcntl
        if (type(deadline) not in (int,float) or not math.isfinite(deadline) or not callable(authorize)):
            raise NativeReadAdmissionHeld('An exact read deadline and current authority are required')
        slot=None
        with ExitStack() as stack:
            parent,_=stack.enter_context(private_parent(self._path('.lock')))
            fd=self._open_lock(parent,'.lock');stack.callback(os.close,fd)
            slots=[]
            for index in range(self.policy.max_concurrent):
                value=self._open_lock(parent,f'.slot-{index:02d}.lock')
                stack.callback(os.close,value);slots.append(value)
            while slot is None:
                self.check();authorize();self.check()
                if time.monotonic()>=deadline:raise NativeReadAdmissionHeld('Shared read admission deadline expired')
                try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:
                    self._stopped.wait(min(.05,max(0,deadline-time.monotonic())));continue
                try:
                    self.check()
                    if read_private(self._path('.policy.json'),2048)!=_json(self._policy).encode('ascii'):
                        raise NativeReadAdmissionHeld('Endpoint budget policy changed')
                    at=self._clock()
                    if not _utc(at):raise NativeReadAdmissionHeld('Shared endpoint clock is invalid')
                    rate=self._rate()
                    if rate is None:raise NativeReadAdmissionHeld('Endpoint rate reservation is missing')
                    if at<rate[0]:raise NativeReadAdmissionHeld('Shared endpoint clock regressed')
                    if at>=rate[1]:
                        for value in slots:
                            try:fcntl.flock(value,fcntl.LOCK_EX|fcntl.LOCK_NB)
                            except BlockingIOError:continue
                            slot=value
                            self._reserve(parent,at)
                            break
                finally:fcntl.flock(fd,fcntl.LOCK_UN)
                if slot is None:self._stopped.wait(min(.05,max(0,deadline-time.monotonic())))
            try:
                self.check();authorize();self.check()
                if time.monotonic()>=deadline:raise NativeReadAdmissionHeld('Shared read deadline expired after admission')
                yield
            finally:fcntl.flock(slot,fcntl.LOCK_UN)
