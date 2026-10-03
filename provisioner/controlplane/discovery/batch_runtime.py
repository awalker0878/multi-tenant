"""One bounded dispatch of already authorized discovery campaigns.

Batch policy selects work and reduces native read rates. It does not issue a
campaign, refresh credentials, publish inventory, retry work, or persist a fleet
schedule by default. Opt-in checkpointed scheduling retains starts and outcomes;
original-byte staging/recovery stays with the existing collector.
"""
from __future__ import annotations

import hashlib
import re
import time
from collections import defaultdict, deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Timer
from typing import Callable

from .collector_runtime import execute
from .collector_settings import protected_path
from .model import _id, _utc
from .native_credentials import NativeReadHeld, decode_json, read_protected
from .read_budget import EndpointReadPolicy, NativeReadGate
from .trust import _keys

FORMAT = 'hosting-discovery-batch-outcome/1'
MAX_BYTES = 131072
_SHA = re.compile(r'^[0-9a-f]{64}$')


def _digest(value):
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ValueError('An exact SHA-256 reference is required')
    return value


def _timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('A bounded UTC timestamp is required')
    at = datetime.fromisoformat(value)
    if not _utc(at):
        raise ValueError('A UTC schedule window is required')
    return at


@dataclass(frozen=True, slots=True)
class BatchTask:
    task_id: str
    environment_id: str
    campaign_digest: str
    config_file: Path
    config_digest: str
    policy_id: str
    not_before: datetime
    not_after: datetime


@dataclass(frozen=True, slots=True)
class DiscoveryBatch:
    batch_id: str
    digest: str
    parallel: int
    max_seconds: int
    policies: tuple[tuple[str, EndpointReadPolicy], ...]
    tasks: tuple[BatchTask, ...]

    @classmethod
    def from_file(cls, path):
        raw = read_protected(protected_path(str(path)), MAX_BYTES)
        doc = _keys(decode_json(raw, MAX_BYTES), {'format', 'batchId', 'maxParallelCollections',
                    'maxDurationSeconds', 'endpoints', 'tasks'})
        if (doc['format'] != 'hosting-discovery-batch/1' or not _id(doc['batchId'])
                or type(doc['maxParallelCollections']) is not int or not 1 <= doc['maxParallelCollections'] <= 16
                or type(doc['maxDurationSeconds']) is not int or not 1 <= doc['maxDurationSeconds'] <= 3600
                or not isinstance(doc['endpoints'], list) or not 1 <= len(doc['endpoints']) <= 64
                or not isinstance(doc['tasks'], list) or not 1 <= len(doc['tasks']) <= 128):
            raise ValueError('Bounded batch settings are required')
        policies, policy_ids, endpoints = [], set(), set()
        for row in doc['endpoints']:
            _keys(row, {'policyId', 'organizationId', 'siteId', 'platformFamily', 'endpointId',
                        'maxConcurrentReads', 'minReadIntervalMilliseconds'})
            policy = EndpointReadPolicy(row['organizationId'], row['siteId'], row['platformFamily'],
                row['endpointId'], row['maxConcurrentReads'], row['minReadIntervalMilliseconds'])
            if not _id(row['policyId']) or row['policyId'] in policy_ids or policy.key in endpoints:
                raise ValueError('Each native endpoint needs one unambiguous read policy')
            policy_ids.add(row['policyId']); endpoints.add(policy.key)
            policies.append((row['policyId'], policy))
        tasks, task_ids, campaigns, config_files = [], set(), set(), set()
        for row in doc['tasks']:
            _keys(row, {'taskId', 'environmentId', 'campaignDigest', 'collectorConfigFile',
                        'collectorConfigDigest', 'policyId', 'notBefore', 'notAfter'})
            start, end = _timestamp(row['notBefore']), _timestamp(row['notAfter'])
            file = protected_path(row['collectorConfigFile'])
            campaign = _digest(row['campaignDigest'])
            if (not all(_id(row[k]) for k in ('taskId', 'environmentId', 'policyId'))
                    or row['taskId'] in task_ids or campaign in campaigns or file in config_files
                    or row['policyId'] not in policy_ids or not start < end
                    or end - start > timedelta(hours=1)):
                raise ValueError('Unique exact campaigns and bounded task windows are required')
            task_ids.add(row['taskId']); campaigns.add(campaign); config_files.add(file)
            tasks.append(BatchTask(row['taskId'], row['environmentId'], campaign, file,
                _digest(row['collectorConfigDigest']), row['policyId'], start, end))
        return cls(doc['batchId'], hashlib.sha256(raw).hexdigest(), doc['maxParallelCollections'],
                   doc['maxDurationSeconds'], tuple(policies), tuple(tasks))


def run_batch(path, *, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
              state_directory=None, wait_for_due=False, fleet_state_directory=None) -> dict:
    if type(wait_for_due) is not bool or wait_for_due and state_directory is None:
        raise ValueError('Waiting requires an explicit durable batch journal')
    spec = DiscoveryBatch.from_file(path)
    if state_directory is None:
        return _run_batch(spec, clock=clock, fleet_state_directory=fleet_state_directory)
    from .batch_journal import BatchJournal
    with BatchJournal(state_directory, spec, manifest_path=path, clock=clock, enroll=True) as journal:
        return _run_batch(spec, clock=clock, journal=journal, wait_for_due=wait_for_due,
                          fleet_state_directory=fleet_state_directory)


def _run_batch(spec, *, clock, journal=None, wait_for_due=False, fleet_state_directory=None) -> dict:
    """Use one dispatcher; optionally wait for pre-enrolled future tasks.

    Due tasks are round-robin across selected endpoints, oldest first within each
    endpoint. The process bounds both active collections and actual native GETs.
    A shared stop event stops new reads and results after the duration limit.
    Running threads are drained, never left collecting after this function returns.
    """
    initial = journal.now() if journal is not None else clock()
    if not _utc(initial):
        raise ValueError('A trusted UTC batch clock is required')
    stopped = Event()
    deadline = time.monotonic() + spec.max_seconds
    if fleet_state_directory is None:
        gates = {name: NativeReadGate(policy, stopped=stopped) for name, policy in spec.policies}
    else:
        from .shared_read_budget import SharedNativeReadGate
        gates = {name: SharedNativeReadGate(policy, stopped=stopped, directory=fleet_state_directory)
                 for name, policy in spec.policies}
    results, groups, future_tasks = {}, defaultdict(deque), []
    for task in sorted(spec.tasks, key=lambda t: (t.not_before, t.task_id)):
        recorded = journal.summary(task.task_id) if journal is not None else None
        if recorded is not None:
            results[task.task_id] = recorded
        elif initial < task.not_before:
            results[task.task_id] = {'taskId': task.task_id, 'status': 'NOT_DUE'}
            if wait_for_due:
                future_tasks.append(task)
        elif initial >= task.not_after:
            if journal is not None:
                journal.expire(task.task_id)
            results[task.task_id] = {'taskId': task.task_id, 'status': 'WINDOW_EXPIRED'}
        else:
            groups[task.policy_id].append(task)
    ready = deque()
    def enqueue_due():
        while groups:
            for name in tuple(groups):
                ready.append(groups[name].popleft())
                if not groups[name]:
                    del groups[name]
    enqueue_due()

    def run(task):
        previous = initial

        def current():
            nonlocal previous
            at = journal.now() if journal is not None else clock()
            if (stopped.is_set() or time.monotonic() >= deadline or not _utc(at)
                    or not previous <= at or not task.not_before <= at < task.not_after):
                raise NativeReadHeld('Scheduled collection expired, stopped or clock regressed')
            previous = at
            return at

        started = False
        try:
            current()
            if journal is not None:
                journal.start(task.task_id)
                started = True
            outcome = execute(task.config_file, 'stage', clock=current,
                config_digest=task.config_digest, campaign_digest=task.campaign_digest,
                environment_id=task.environment_id, read_gate=gates[task.policy_id])
            if journal is not None:
                journal.finish(task.task_id, outcome)
            return {'taskId': task.task_id, 'status': 'STAGED', 'collector': outcome}
        except Exception:
            # No private file paths, token material or native error bodies escape.
            # A hold can still have retained original bytes; it does not mean rollback.
            if journal is not None and started:
                try:
                    journal.finish(task.task_id)
                except Exception:
                    stopped.set()  # Publication may have succeeded; never overwrite/retry it.
            return {'taskId': task.task_id, 'status': 'HELD', 'reconciliationRequired': True}

    timer = Timer(spec.max_seconds, stopped.set)
    timer.daemon = True
    executor = ThreadPoolExecutor(max_workers=spec.parallel, thread_name_prefix='discovery-batch')
    active = {}
    timer.start()
    try:
        while ready or active or future_tasks:
            if future_tasks and not stopped.is_set():
                at = journal.now()
                # The same gate/timer/lock survives waits. No interval is reset
                # when another endpoint's task becomes due later in this run.
                for task in tuple(future_tasks):
                    if at >= task.not_after:
                        journal.expire(task.task_id)
                        results[task.task_id] = {'taskId': task.task_id, 'status': 'WINDOW_EXPIRED'}
                        future_tasks.remove(task)
                    elif at >= task.not_before:
                        groups[task.policy_id].append(task)
                        results.pop(task.task_id, None)
                        future_tasks.remove(task)
                enqueue_due()
            while ready and len(active) < spec.parallel and not stopped.is_set():
                if time.monotonic() >= deadline:
                    stopped.set()
                    break
                task = ready.popleft()
                active[executor.submit(run, task)] = task
            if not active:
                if future_tasks and not stopped.is_set() and time.monotonic() < deadline:
                    stopped.wait(min(0.05, max(0, deadline - time.monotonic())))
                    continue
                break
            done, _ = wait(active, timeout=0.05, return_when=FIRST_COMPLETED)
            for future in done:
                task = active.pop(future)
                results[task.task_id] = future.result()
    finally:
        stopped.set()
        # Cooperative cancellation is rechecked by native reads and before signing.
        # A blocked native socket may take its remaining bounded timeout to close.
        executor.shutdown(wait=True, cancel_futures=True)
        timer.cancel()
        timer.join()
    for task in ready:
        results[task.task_id] = {'taskId': task.task_id, 'status': 'NOT_STARTED'}
    items = [results[t.task_id] for t in spec.tasks]
    held = any(item['status'] not in ('STAGED', 'NOT_DUE') and not (
        item['status'] == 'ALREADY_RECORDED' and item['recordedEvent'] in
        ('TASK_STAGED', 'TASK_RECONCILED', 'TASK_PUBLISHED')) for item in items)
    result = {'format': FORMAT, 'batchId': spec.batch_id, 'batchDigest': spec.digest,
        'checkedAt': initial.isoformat(), 'status': 'BATCH_HELD' if held else 'BATCH_EVALUATED',
        'stagedCount': sum(item['status'] == 'STAGED' for item in items),
        'items': items, 'limitScope': 'THIS_PROCESS_ONLY', 'durableSchedule': False,
        'publicationAttempted': False, 'executionAuthorized': False}
    if journal is not None:
        result.update(format='hosting-discovery-checkpointed-batch-outcome/1',
                      durableSchedule=True, scheduleScope='ONE_LOCAL_BATCH_JOURNAL',
                      journalRecordDigest=journal._previous, journalSequence=journal._sequence,
                      unresolvedTaskCount=sum(item['status'] in ('OUTCOME_UNKNOWN', 'DELIVERY_UNKNOWN', 'HELD') for item in items),
                      historicalOnly=False, waitedForDue=wait_for_due,
                      pendingTaskCount=sum(item['status'] in ('NOT_DUE', 'NOT_STARTED') for item in items))
    if fleet_state_directory is not None:
        result.update(limitScope='ONE_SHARED_POSIX_COORDINATOR_HOST', durableEndpointBudget=True)
    return result


def inspect_batch(path, state_directory, *, reconcile=False,
                  clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> dict:
    """Read retained scheduling state, optionally reconcile original signed custody.

    A reconciliation invokes only collector `inspect`, never `stage` or `publish`.
    Absence, incomplete original custody, revoked/expired authority or changed inputs
    stay unresolved. This method cannot reset a started task or issue another capture.
    """
    from .batch_journal import BatchJournal, validate_staged
    if type(reconcile) is not bool:
        raise ValueError('Reconciliation must be selected explicitly')
    spec = DiscoveryBatch.from_file(path)
    with BatchJournal(state_directory, spec, manifest_path=path, clock=clock) as journal:
        initial = journal.now()
        deadline = time.monotonic() + spec.max_seconds
        items = []
        for task in spec.tasks:
            row = journal.summary(task.task_id)
            if row is None:
                row = {'taskId': task.task_id, 'status': 'NOT_STARTED', 'historicalOnly': True,
                       'reconciliationRequired': False}
            if reconcile and row['status'] == 'OUTCOME_UNKNOWN':
                def current():
                    if time.monotonic() >= deadline:
                        raise NativeReadHeld('Batch reconciliation deadline expired')
                    return journal.now()
                try:
                    current()
                    value = execute(task.config_file, 'inspect', clock=current,
                        config_digest=task.config_digest, campaign_digest=task.campaign_digest,
                        environment_id=task.environment_id)
                    # The installed collector rechecks original campaign/result signatures.
                    # Here we only guard the exact returned binding before checkpointing it.
                    _keys(value, {'format', 'status', 'campaignId', 'environmentId', 'authorizationDigest',
                        'checkedAt', 'collectionIntent', 'original', 'consistency', 'publicationStatus',
                        'reconciliationRequired', 'localCustodyOnly', 'collectionRequested',
                        'publicationAttempted', 'executionAuthorized'})
                    if (value['format'] != 'hosting-discovery-outbox-inspection/1'
                            or value['status'] != 'STAGED_ORIGINAL' or not _id(value['campaignId'])
                            or value['environmentId'] != task.environment_id
                            or value['authorizationDigest'] != task.campaign_digest
                            or value['consistency'] != 'LOCAL_RECORDS_RECHECKED'
                            or value['publicationStatus'] != 'NOT_CHECKED' or value['localCustodyOnly'] is not True
                            or any(value[k] is not False for k in ('reconciliationRequired',
                                'collectionRequested', 'publicationAttempted', 'executionAuthorized'))
                            or not initial <= _timestamp(value['checkedAt']) <= current()):
                        raise NativeReadHeld('Original inspection differs from the scheduled task')
                    original = _keys(value['original'], {'requestDigest', 'resultDigest', 'capturedAt',
                                                       'completeness', 'objectCount'})
                    captured = _timestamp(original['capturedAt'])
                    if captured > _timestamp(value['checkedAt']):
                        raise NativeReadHeld('Original capture time is inconsistent')
                    outcome = {'format': 'hosting-discovery-collector-outcome/1', 'status': 'STAGED',
                        'campaignId': value['campaignId'], 'environmentId': task.environment_id,
                        'requestDigest': original['requestDigest'], 'resultDigest': original['resultDigest'],
                        'completeness': original['completeness'], 'objectCount': original['objectCount'],
                        'collectionRequested': False, 'publicationAttempted': False, 'executionAuthorized': False}
                    validate_staged(outcome, task.environment_id)
                    journal.finish(task.task_id, outcome, recovered=True)
                    row = journal.summary(task.task_id)
                except Exception:
                    # Do not append repeated failure records or change the original start.
                    row = {**row, 'reconciliationStatus': 'HELD'}
            items.append(row)
        unresolved = sum(item['status'] in ('OUTCOME_UNKNOWN', 'DELIVERY_UNKNOWN') for item in items)
        return {'format': 'hosting-discovery-batch-journal-inspection/1',
            'batchId': spec.batch_id, 'batchDigest': spec.digest, 'checkedAt': initial.isoformat(),
            'status': 'JOURNAL_HELD' if unresolved else 'JOURNAL_INSPECTED',
            'items': items, 'unresolvedTaskCount': unresolved,
            'journalRecordDigest': journal._previous, 'journalSequence': journal._sequence,
            'reconciliationRequested': reconcile, 'historicalOnly': True,
            'scheduleScope': 'ONE_LOCAL_BATCH_JOURNAL', 'durableSchedule': True,
            'collectionRequested': False, 'publicationAttempted': False, 'executionAuthorized': False}


def publish_batch(path, state_directory, *, retry_unknown=False,
                  clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> dict:
    """Deliver retained originals with current authority; never collect or re-sign.

    Every attempt is durably recorded before the existing mTLS publisher is called.
    Lost replies or process exits require an explicitly selected original-byte retry.
    A publication receipt is retained only when its exact original digest matches.
    """
    from .batch_journal import BatchJournal, validate_published
    if type(retry_unknown) is not bool:
        raise ValueError('Original-only replay must be selected explicitly')
    spec = DiscoveryBatch.from_file(path)
    with BatchJournal(state_directory, spec, manifest_path=path, clock=clock) as journal:
        initial = journal.now()
        deadline = time.monotonic() + spec.max_seconds
        items = []
        for task in spec.tasks:
            row = journal.summary(task.task_id)
            original = journal.original(task.task_id)
            if row is not None and row.get('recordedEvent') == 'TASK_PUBLISHED':
                items.append(row)
                continue
            if (original is None or row is None or row['status'] == 'DELIVERY_UNKNOWN' and not retry_unknown):
                items.append(row or {'taskId': task.task_id, 'status': 'ORIGINAL_NOT_RETAINED',
                    'historicalOnly': True, 'reconciliationRequired': True})
                continue
            started = False
            def current():
                at = journal.now()
                if time.monotonic() >= deadline or not task.not_before <= at < task.not_after:
                    raise NativeReadHeld('Publication window or deadline expired')
                return at
            try:
                current()
                journal.publication_start(task.task_id)
                started = True
                outcome = execute(task.config_file, 'publish', clock=current,
                    config_digest=task.config_digest, campaign_digest=task.campaign_digest,
                    environment_id=task.environment_id)
                validate_published(outcome, original)
                journal.publication_finish(task.task_id, outcome)
                items.append({'taskId': task.task_id, 'status': 'PUBLISHED', 'collector': outcome,
                              'historicalOnly': False, 'reconciliationRequired': False})
            except Exception:
                if started:
                    # Even an error before sending does not erase the retained start.
                    # Never recollect or clear an uncertain native/publication effect.
                    try:
                        journal.publication_finish(task.task_id)
                    except Exception:
                        raise NativeReadHeld('Publication checkpoint requires reopening and reconciliation') from None
                items.append({'taskId': task.task_id, 'status': 'DELIVERY_UNKNOWN' if started else 'PUBLICATION_HELD',
                              'historicalOnly': False, 'reconciliationRequired': True})
        unknown = sum(item['status'] == 'DELIVERY_UNKNOWN' for item in items)
        held = any(item['status'] != 'PUBLISHED' and not (
            item['status'] == 'ALREADY_RECORDED' and item['recordedEvent'] == 'TASK_PUBLISHED') for item in items)
        return {'format': 'hosting-discovery-batch-publication-outcome/1',
            'batchId': spec.batch_id, 'batchDigest': spec.digest, 'checkedAt': initial.isoformat(),
            'status': 'PUBLICATION_HELD' if held else 'PUBLICATION_ACKNOWLEDGED',
            'items': items, 'publishedCount': sum(item['status'] == 'PUBLISHED' for item in items),
            'unknownDeliveryCount': unknown, 'journalRecordDigest': journal._previous,
            'journalSequence': journal._sequence, 'retryUnknownRequested': retry_unknown,
            'durableSchedule': True, 'scheduleScope': 'ONE_LOCAL_BATCH_JOURNAL',
            'collectionRequested': False, 'publicationAttempted': any(
                item['status'] in ('PUBLISHED', 'DELIVERY_UNKNOWN') and item.get('historicalOnly') is False
                for item in items), 'executionAuthorized': False}
