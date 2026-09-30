"""One bounded dispatch of already authorized discovery campaigns.

Batch policy selects work and reduces native read rates. It does not issue a
campaign, refresh credentials, publish inventory, retry work, or persist a fleet
schedule. Original-byte staging/recovery stays with the existing collector.
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


def run_batch(path, *, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> dict:
    """Dispatch only tasks due at the initial cut; never wait for future work.

    Due tasks are round-robin across selected endpoints, oldest first within each
    endpoint. The process bounds both active collections and actual native GETs.
    A shared stop event stops new reads and results after the duration limit.
    Running threads are drained, never left collecting after this function returns.
    """
    spec = DiscoveryBatch.from_file(path)
    initial = clock()
    if not _utc(initial):
        raise ValueError('A trusted UTC batch clock is required')
    stopped = Event()
    deadline = time.monotonic() + spec.max_seconds
    gates = {name: NativeReadGate(policy, stopped=stopped) for name, policy in spec.policies}
    results, groups = {}, defaultdict(deque)
    for task in sorted(spec.tasks, key=lambda t: (t.not_before, t.task_id)):
        if initial < task.not_before:
            results[task.task_id] = {'taskId': task.task_id, 'status': 'NOT_DUE'}
        elif initial >= task.not_after:
            results[task.task_id] = {'taskId': task.task_id, 'status': 'WINDOW_EXPIRED'}
        else:
            groups[task.policy_id].append(task)
    ready = deque()
    while groups:
        for name in tuple(groups):
            ready.append(groups[name].popleft())
            if not groups[name]:
                del groups[name]

    def run(task):
        previous = initial

        def current():
            nonlocal previous
            at = clock()
            if (stopped.is_set() or time.monotonic() >= deadline or not _utc(at)
                    or not previous <= at or not task.not_before <= at < task.not_after):
                raise NativeReadHeld('Scheduled collection expired, stopped or clock regressed')
            previous = at
            return at

        try:
            current()
            outcome = execute(task.config_file, 'stage', clock=current,
                config_digest=task.config_digest, campaign_digest=task.campaign_digest,
                environment_id=task.environment_id, read_gate=gates[task.policy_id])
            return {'taskId': task.task_id, 'status': 'STAGED', 'collector': outcome}
        except Exception:
            # No private file paths, token material or native error bodies escape.
            # A hold can still have retained original bytes; it does not mean rollback.
            return {'taskId': task.task_id, 'status': 'HELD', 'reconciliationRequired': True}

    timer = Timer(spec.max_seconds, stopped.set)
    timer.daemon = True
    executor = ThreadPoolExecutor(max_workers=spec.parallel, thread_name_prefix='discovery-batch')
    active = {}
    timer.start()
    try:
        while ready or active:
            while ready and len(active) < spec.parallel and not stopped.is_set():
                if time.monotonic() >= deadline:
                    stopped.set()
                    break
                task = ready.popleft()
                active[executor.submit(run, task)] = task
            if not active:
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
    held = any(item['status'] not in ('STAGED', 'NOT_DUE') for item in items)
    return {'format': FORMAT, 'batchId': spec.batch_id, 'batchDigest': spec.digest,
        'checkedAt': initial.isoformat(), 'status': 'BATCH_HELD' if held else 'BATCH_EVALUATED',
        'stagedCount': sum(item['status'] == 'STAGED' for item in items),
        'items': items, 'limitScope': 'THIS_PROCESS_ONLY', 'durableSchedule': False,
        'publicationAttempted': False, 'executionAuthorized': False}
