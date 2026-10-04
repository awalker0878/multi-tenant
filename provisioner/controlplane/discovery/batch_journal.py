"""Restart-safe state for one finite, preauthorized discovery batch.

This journal coordinates cooperating processes sharing one private local directory.
It grants no collection authority, never clears a started task for retry, and is not
an enterprise scheduler or independent audit store. Restore/rollback of its complete
history requires external custody and reconciliation with the original outboxes.
"""
from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime
import hashlib
import os
from pathlib import Path
import re
import stat
from threading import RLock

from .model import _id, _json, _utc
from .native_credentials import decode_json, read_protected
from .review_files import private_parent, publish_once, read_private
from .trust import _keys

MAX_RECORD_BYTES = 8192
MAX_PUBLICATION_ATTEMPTS = 3
MAX_RECORDS = 1153  # enrollment plus three capture and six publication records/task
_FIELDS = {'format', 'sequence', 'batchId', 'batchDigest', 'previousRecordDigest',
           'recordedAt', 'event', 'taskId', 'outcome', 'recordDigest'}


def _digest(value):
    return hashlib.sha256(_json(value).encode('ascii')).hexdigest()


def _stamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('Invalid batch journal timestamp')
    at = datetime.fromisoformat(value)
    if not _utc(at):
        raise ValueError('UTC batch journal timestamps required')
    return at


def _sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def validate_staged(value, environment_id):
    """Retained collector metadata is a checkpoint, not a current signed review."""
    _keys(value, {'format', 'status', 'campaignId', 'environmentId', 'requestDigest',
                  'resultDigest', 'completeness', 'objectCount', 'collectionRequested',
                  'publicationAttempted', 'executionAuthorized'})
    if (value['format'] != 'hosting-discovery-collector-outcome/1' or value['status'] != 'STAGED'
            or not _id(value['campaignId']) or value['environmentId'] != environment_id
            or not _sha(value['requestDigest']) or not _sha(value['resultDigest'])
            or value['completeness'] not in ('COMPLETE', 'PARTIAL', 'UNKNOWN')
            or type(value['objectCount']) is not int or not 0 <= value['objectCount'] < 2**63
            or type(value['collectionRequested']) is not bool
            or value['publicationAttempted'] is not False or value['executionAuthorized'] is not False):
        raise ValueError('Invalid staged batch checkpoint')
    return deepcopy(value)


def validate_published(value, original):
    """An authenticated receipt must identify the exact retained original."""
    _keys(value, {'format', 'status', 'campaignId', 'environmentId', 'requestDigest',
                  'resultDigest', 'generation', 'completeness', 'collectionRequested',
                  'publicationAttempted', 'executionAuthorized'})
    if (value['format'] != 'hosting-discovery-collector-outcome/1'
            or value['status'] != 'PUBLISHED'
            or any(value[key] != original[key] for key in
                   ('campaignId', 'environmentId', 'requestDigest', 'resultDigest', 'completeness'))
            or type(value['generation']) is not int or not 1 <= value['generation'] < 2**63
            or value['collectionRequested'] is not False or value['publicationAttempted'] is not True
            or value['executionAuthorized'] is not False):
        raise ValueError('Publication receipt does not identify the retained original')
    return deepcopy(value)


class BatchJournal:
    """Append-only, digest-linked decisions under a process and thread lock.

    The directory must already exist. Only enrollment creates a journal; inspect
    and reconcile require it. The lock file is never deleted. File names are local
    sequence numbers, never caller task IDs or native paths. Partial files, missing
    records, changed manifest bytes and invalid state transitions all hold.
    """
    def __init__(self, directory, spec, *, manifest_path, clock, enroll=False):
        self.directory = Path(directory)
        self.spec, self.manifest_path, self.clock = spec, Path(manifest_path), clock
        self.enroll = enroll
        self._stack = ExitStack()
        self._mutex = RLock()
        self._tasks = {task.task_id: task for task in spec.tasks}
        self._states = {}
        self._originals, self._publication_attempts = {}, {}
        self._sequence, self._previous, self._last = 0, None, None
        self._poisoned = False
        self._observed_at = None
        self._lock = self._parent = None

    def __enter__(self):
        try:
            import fcntl  # POSIX-only selected mode; ordinary batches stay portable.
            path = str(self.directory / 'batch.lock')
            self._parent, name = self._stack.enter_context(private_parent(path))
            info = os.fstat(self._parent)
            if info.st_uid != os.geteuid():
                raise ValueError('Batch state directory must be owned by this service')
            self._directory_identity = (info.st_dev, info.st_ino)
            flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
            if self.enroll:
                flags |= os.O_CREAT
            self._lock = os.open(name, flags, 0o600, dir_fd=self._parent)
            self._stack.callback(os.close, self._lock)
            lock = os.fstat(self._lock)
            if (not stat.S_ISREG(lock.st_mode) or lock.st_uid != os.geteuid()
                    or lock.st_mode & 0o077 or lock.st_nlink != 1 or lock.st_size != 0):
                raise ValueError('Batch lock is not a private single-link regular file')
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fsync(self._parent)
            self.check()
            # The directory is intentionally small and exclusively owned by this batch.
            names = os.listdir(self._parent)
            if len(names) > MAX_RECORDS + 1 or any(
                    name != 'batch.lock' and re.fullmatch('[0-9]{6}\\.json', name) is None for name in names):
                raise ValueError('Unexpected or excessive batch journal members')
            files = sorted(name for name in names if name != 'batch.lock')
            for number, name in enumerate(files, 1):
                if name != f'{number:06d}.json':
                    raise ValueError('Batch journal sequence is incomplete')
                raw = read_private(str(self.directory / name), MAX_RECORD_BYTES)
                value = decode_json(raw, MAX_RECORD_BYTES)
                if _json(value).encode('ascii') != raw:
                    raise ValueError('Batch journal record is not canonical')
                self._accept(value)
            self.now()
            if not files:
                if not self.enroll:
                    raise ValueError('An enrolled batch journal is required')
                self._append('ENROLLED', None, None, self.now())
            return self
        except BaseException:
            self._stack.close()
            raise

    def __exit__(self, *args):
        self._stack.close()
        self._lock = self._parent = None

    def check(self):
        if self._poisoned or self._parent is None or self._lock is None:
            raise ValueError('Batch journal is held or closed')
        # Reopen only to compare identity; a renamed/replaced state directory must
        # not leave us acting under an obsolete lock while another writer starts.
        with private_parent(str(self.directory / 'batch.lock')) as (parent, name):
            current = os.fstat(parent)
            linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
            locked = os.fstat(self._lock)
            if ((current.st_dev, current.st_ino) != self._directory_identity
                    or (linked.st_dev, linked.st_ino) != (locked.st_dev, locked.st_ino)
                    or not stat.S_ISREG(linked.st_mode) or linked.st_nlink != 1
                    or linked.st_mode & 0o077 or linked.st_uid != os.geteuid()):
                raise ValueError('Batch journal/lock identity changed')
        raw = read_protected(self.manifest_path, 131072)
        if hashlib.sha256(raw).hexdigest() != self.spec.digest:
            raise ValueError('Batch manifest changed after enrollment')

    def now(self):
        with self._mutex:
            self.check()
            at = self.clock()
            if (not _utc(at) or self._last is not None and at < self._last
                    or self._observed_at is not None and at < self._observed_at):
                raise ValueError('Batch clock regressed behind retained history')
            self._observed_at = at
            return at

    def state(self, task_id):
        with self._mutex:
            self.check()
            if task_id not in self._tasks:
                raise ValueError('Unknown batch task')
            return deepcopy(self._states.get(task_id))

    def _accept(self, row):
        _keys(row, _FIELDS)
        body = {key: value for key, value in row.items() if key != 'recordDigest'}
        at = _stamp(row['recordedAt'])
        if (row['format'] != 'hosting-discovery-batch-journal-record/1'
                or type(row['sequence']) is not int or row['sequence'] != self._sequence + 1
                or row['sequence'] > MAX_RECORDS or row['batchId'] != self.spec.batch_id
                or row['batchDigest'] != self.spec.digest
                or row['previousRecordDigest'] != self._previous
                or row['recordDigest'] != _digest(body)
                or self._last is not None and at < self._last):
            raise ValueError('Batch journal identity, digest or chronology differs')
        event, task_id, outcome = row['event'], row['taskId'], row['outcome']
        if self._sequence == 0:
            if event != 'ENROLLED' or task_id is not None or outcome is not None:
                raise ValueError('Batch enrollment must be the first record')
        else:
            if not isinstance(task_id, str) or task_id not in self._tasks:
                raise ValueError('Journal task is not in the enrolled manifest')
            task, prior = self._tasks[task_id], self._states.get(task_id)
            previous = None if prior is None else prior['event']
            if event == 'TASK_STARTED':
                if previous is not None or outcome is not None or not task.not_before <= at < task.not_after:
                    raise ValueError('Task cannot start or restart under this window')
            elif event == 'TASK_EXPIRED':
                if previous is not None or outcome is not None or at < task.not_after:
                    raise ValueError('Invalid expired unstarted task')
            elif event == 'TASK_HELD':
                if previous != 'TASK_STARTED' or outcome is not None:
                    raise ValueError('Only a started task can become held')
            elif event in ('TASK_STAGED', 'TASK_RECONCILED'):
                if previous not in (('TASK_STARTED',) if event == 'TASK_STAGED' else ('TASK_STARTED', 'TASK_HELD')):
                    raise ValueError('Staged completion has no unresolved start')
                validate_staged(outcome, task.environment_id)
                if event == 'TASK_RECONCILED' and outcome['collectionRequested'] is not False:
                    raise ValueError('Reconciliation cannot request collection')
                self._originals[task_id] = deepcopy(outcome)
            elif event == 'TASK_PUBLICATION_STARTED':
                if (previous not in ('TASK_STAGED', 'TASK_RECONCILED',
                                      'TASK_PUBLICATION_STARTED', 'TASK_PUBLICATION_UNKNOWN')
                        or task_id not in self._originals or outcome is not None
                        or not task.not_before <= at < task.not_after
                        or self._publication_attempts.get(task_id, 0) >= MAX_PUBLICATION_ATTEMPTS):
                    raise ValueError('Publication needs an original, current window and bounded attempt')
                self._publication_attempts[task_id] = self._publication_attempts.get(task_id, 0) + 1
            elif event == 'TASK_PUBLICATION_UNKNOWN':
                if previous != 'TASK_PUBLICATION_STARTED' or outcome is not None:
                    raise ValueError('Only a started publication can have an unknown outcome')
            elif event == 'TASK_PUBLISHED':
                if previous != 'TASK_PUBLICATION_STARTED':
                    raise ValueError('An authenticated publication has no prior delivery start')
                validate_published(outcome, self._originals[task_id])
            else:
                raise ValueError('Unknown batch journal transition')
            self._states[task_id] = deepcopy(row)
        self._sequence, self._previous, self._last = row['sequence'], row['recordDigest'], at

    def _append(self, event, task_id, outcome, at):
        self.check()
        row = {'format': 'hosting-discovery-batch-journal-record/1',
            'sequence': self._sequence + 1, 'batchId': self.spec.batch_id,
            'batchDigest': self.spec.digest, 'previousRecordDigest': self._previous,
            'recordedAt': at.isoformat(), 'event': event, 'taskId': task_id, 'outcome': outcome}
        row['recordDigest'] = _digest(row)
        # Validate before any file creation while preserving the prior view.
        old = (self._sequence, self._previous, self._last, deepcopy(self._states),
               deepcopy(self._originals), dict(self._publication_attempts))
        try:
            self._accept(row)
        finally:
            (self._sequence, self._previous, self._last, self._states,
             self._originals, self._publication_attempts) = old
        raw = _json(row).encode('ascii')
        if len(raw) > MAX_RECORD_BYTES:
            raise ValueError('Batch checkpoint exceeds its bound')
        try:
            publish_once(str(self.directory / f'{row["sequence"]:06d}.json'), raw, self.check)
        except BaseException:
            self._poisoned = True  # A final file may exist: reopen and reconcile, never overwrite.
            raise
        self._accept(row)
        return deepcopy(row)

    def start(self, task_id):
        with self._mutex:
            return self._append('TASK_STARTED', task_id, None, self.now())

    def expire(self, task_id):
        with self._mutex:
            return self._append('TASK_EXPIRED', task_id, None, self.now())

    def finish(self, task_id, outcome=None, *, recovered=False):
        with self._mutex:
            event = 'TASK_RECONCILED' if recovered else 'TASK_HELD' if outcome is None else 'TASK_STAGED'
            return self._append(event, task_id, outcome, self.now())

    def original(self, task_id):
        with self._mutex:
            self.check()
            return deepcopy(self._originals.get(task_id))

    def publication_start(self, task_id):
        with self._mutex:
            return self._append('TASK_PUBLICATION_STARTED', task_id, None, self.now())

    def publication_finish(self, task_id, outcome=None):
        with self._mutex:
            event = 'TASK_PUBLICATION_UNKNOWN' if outcome is None else 'TASK_PUBLISHED'
            return self._append(event, task_id, outcome, self.now())

    def summary(self, task_id):
        row = self.state(task_id)
        if row is None:
            return None
        unresolved = row['event'] in ('TASK_STARTED', 'TASK_HELD')
        delivery_unknown = row['event'] in ('TASK_PUBLICATION_STARTED', 'TASK_PUBLICATION_UNKNOWN')
        return {'taskId': task_id, 'status': 'DELIVERY_UNKNOWN' if delivery_unknown else
                'OUTCOME_UNKNOWN' if unresolved else 'ALREADY_RECORDED',
                'recordedEvent': row['event'], 'recordDigest': row['recordDigest'],
                'historicalOnly': True, 'reconciliationRequired': unresolved or delivery_unknown}
