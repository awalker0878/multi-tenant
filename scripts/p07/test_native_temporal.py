"""Native orchestration on real Temporal/TLS/PostgreSQL, with explicitly synthetic owners."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
from threading import Event
from uuid import uuid4

import psycopg
from temporalio.client import Client, WorkflowFailureError
from temporalio.service import TLSConfig
from temporalio.worker import Worker, Replayer

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.domain.native_workflow import PROVISION, RETIRE
from lifecycle.infrastructure.native_journey import NativeJourney
from lifecycle.infrastructure.native_temporal import NativeActivities, NativeDispatcher
from test_native_workflow import native, plan
from native_wire_fixture import native_wire


def test_native_durable_orchestration(native, postgres, tmp_path):
    control, owners, initial = native
    checks = []
    histories = []

    def check(name, value):
        assert value, name
        checks.append({'case': name, 'result': 'PASSED'})

    class Effects:
        def __init__(self):
            self.mode = 'normal'
            self.grants = []
            self.started = Event()
            self.release = Event()

        def execute(self, grant):
            if grant['stage'] == 'provision':
                transport.execute(grant)
                self.grants.append(deepcopy(grant))
                return
            tenant = documents[grant['job_id']]['scope']['tenant_id']
            boundary = 'before_saved_plan_apply' if grant['stage'] == 'provision' else 'before_effect'
            control.boundary(tenant, grant, grant['executor_id'], boundary)
            self.grants.append(deepcopy(grant))
            if self.mode == 'lost_reply':
                raise OSError('private_synthetic_provider_reply')
            if self.mode == 'block':
                self.started.set()
                assert self.release.wait(60), 'fixture_release_timeout'
            control.boundary(tenant, grant, grant['executor_id'], boundary.replace('before', 'during'))

    effects = Effects()
    activities = NativeActivities(control, effects)
    documents = {}
    handles = []

    async def wait_for(label, predicate, seconds=45):
        async with asyncio.timeout(seconds):
            while not predicate():
                await asyncio.sleep(.05)
        check(label, True)

    def document():
        p = plan()
        p['epoch'] = initial['epoch']
        p['scope']['tenant_id'] = initial['scope']['tenant_id']
        p['executor_id'] = initial['executor_id']
        return p

    def admit(p):
        job = control.admit(p, str(uuid4()))
        documents[job] = p
        return job, p['scope']['tenant_id']

    async def scenario():
        client = await Client.connect(
            os.environ['TEMPORAL_TARGET'], namespace='lifecycle',
            tls=TLSConfig(server_root_ca_cert=Path(os.environ['TEMPORAL_CA_FILE']).read_bytes(), domain='temporal'),
            rpc_metadata={'authorization': 'Bearer ' + Path(os.environ['TEMPORAL_CREDENTIAL_FILE']).read_text().strip()},
        )
        executor = ThreadPoolExecutor(max_workers=8)

        def worker():
            return Worker(client, task_queue='p07-native-v1', workflows=[NativeJourney],
                          activities=[activities.checkpoint, activities.prepare, activities.effect, activities.reconcile, activities.hold],
                          activity_executor=executor, graceful_shutdown_timeout=timedelta(seconds=5))

        async def dispatch(job):
            await NativeDispatcher(control.database, client).dispatch()
            handle = client.get_workflow_handle('p07-native-v1-' + job)
            handles.append(handle)
            return handle

        async def ended(handle, state):
            result = await asyncio.wait_for(handle.result(), timeout=45)
            check('terminal-' + state, result == {'state': state, 'native_qualification': 'not_established'})

        try:
            async with worker():
                # The actual start is accepted, but the dispatcher loses its response.
                p = document(); job, tenant = admit(p)

                class LostStart:
                    async def start_workflow(self, *args, **kwargs):
                        await client.start_workflow(*args, **kwargs)
                        raise TimeoutError('synthetic_accepted_temporal_start')

                try:
                    await NativeDispatcher(control.database, LostStart()).dispatch()
                except TimeoutError:
                    check('accepted-start-response-loss', True)
                else:
                    raise AssertionError('fault_not_injected')
                handle = await dispatch(job)
                await ended(handle, 'active')
                check('five-ordered-provision-effects', [g['stage'] for g in effects.grants if g['job_id'] == job] == list(PROVISION))
                check('one-dispatch-after-lost-reply', await NativeDispatcher(control.database, client).dispatch() == 0)

                retirement = deepcopy(p)
                retirement.update(purpose='retire', source_job_id=job, plan_id=str(uuid4()), approval_id=str(uuid4()), plan_digest='b'*64,
                                  intents={stage: digest(stage) for stage in RETIRE})
                retiring, rt = admit(retirement)
                await ended(await dispatch(retiring), 'retired')
                check('retire-before-release', [g['stage'] for g in effects.grants if g['job_id'] == retiring] == list(RETIRE))

                # No process return can substitute for independent provider quiescence.
                owners.omit = 'provider_requests_quiescent'
                denied, dt = admit(document()); denied_handle = await dispatch(denied)
                await wait_for('quiescence-missing-holds', lambda: control.read(dt, denied)['state'] == 'held')
                check('no-following-stage-without-quiescence', len([g for g in effects.grants if g['job_id'] == denied]) == 1)
                owners.omit = None
                control.stop(dt, denied)
                await denied_handle.signal(NativeJourney.wake, control.read(dt, denied)['revision'])
                await ended(denied_handle, 'stopped')

                # Authority can change after durable admission but before any native boundary.
                revoked, vt = admit(document())
                owners.authority_changes['configuration_current'] = False
                revoked_handle = await dispatch(revoked)
                await wait_for('queued-configuration-change-holds', lambda: control.read(vt, revoked)['state'] == 'held')
                check('revocation-has-no-effect', not any(g['job_id'] == revoked for g in effects.grants))
                owners.authority_changes.clear()
                control.stop(vt, revoked)
                await revoked_handle.signal(NativeJourney.wake, control.read(vt, revoked)['revision'])
                await ended(revoked_handle, 'stopped')

                # Accepted effect, lost response: retain grant, hold, and restart the worker.
                effects.mode = 'lost_reply'
                lost, lt = admit(document()); lost_handle = await dispatch(lost)
                await wait_for('lost-effect-response-holds', lambda: control.read(lt, lost)['state'] == 'held')
                lost_grant = next(g for g in effects.grants if g['job_id'] == lost)
                await lost_handle.signal(NativeJourney.wake, control.read(lt, lost)['revision'] + 10)
                check('wake-does-not-clear-hold', control.read(lt, lost)['state'] == 'held')

            # New SDK worker instance must recover the persisted history and journal.
            effects.mode = 'normal'
            async with worker():
                check('same-start-after-worker-restart', await NativeDispatcher(control.database, client).dispatch() == 0)
                check('held-grant-survives-restart', control.read(lt, lost)['operations'][0]['redeemed'])
                control.reconcile(lt, lost_grant)
                await lost_handle.signal(NativeJourney.wake, control.read(lt, lost)['revision'] + 11)
                await ended(lost_handle, 'active')
                check('accepted-effect-not-repeated', len([g for g in effects.grants if g['job_id'] == lost and g['stage'] == 'reserve']) == 1)

                # Cancellation while an accepted operation is still running cannot report drain.
                effects.mode = 'block'; effects.started.clear(); effects.release.clear()
                cancelled, ct = admit(document()); cancelled_handle = await dispatch(cancelled)
                await wait_for('accepted-effect-still-running', effects.started.is_set)
                await cancelled_handle.cancel()
                await wait_for('temporal-cancellation-persists-hold', lambda: control.read(ct, cancelled)['state'] == 'held')
                check('cancellation-does-not-confirm-drain', control.read(ct, cancelled)['operations'][0]['observation_digest'] is None)
                effects.release.set()
                try:
                    await asyncio.wait_for(cancelled_handle.result(), timeout=20)
                except WorkflowFailureError:
                    check('cancelled-workflow-remains-cancelled', True)
                else:
                    raise AssertionError('cancelled_workflow_reported_success')
                check('cancelled-native-hold-retained', control.read(ct, cancelled)['state'] == 'held')

            for handle in handles:
                history = await handle.fetch_history()
                await Replayer(workflows=[NativeJourney]).replay_workflow(history)
                scheduled = [event.activity_task_scheduled_event_attributes for event in history.events if event.HasField('activity_task_scheduled_event_attributes')]
                check('every-activity-disables-retry', all(a.retry_policy.maximum_attempts == 1 for a in scheduled))
                check('history-redacts-private-provider-message', 'private_synthetic_provider_reply' not in history.to_json())
                histories.append({'workflow_id': handle.id, 'events': len(history.events), 'replay': 'PASSED'})
            check('six-real-native-histories-replayed', len(histories) == 6)
            check('two-provision-effects-crossed-real-tls', calls['effect'] == 2 and len(calls['applies']) == 2)
            check('eight-live-boundary-callbacks-crossed-real-tls', calls['boundary'] == 8)
            with worker_connect() as database:
                check('worker-journal-retains-two-claims', database.execute('SELECT count(*) AS total FROM native.attempts').fetchone()['total'] == 2)
                check('worker-journal-retains-two-holds', database.execute('SELECT count(*) AS total FROM native.workspace_holds').fetchone()['total'] == 2)
                check('worker-journal-retains-eight-events', database.execute('SELECT count(*) AS total FROM native.events').fetchone()['total'] == 8)
            try:
                with psycopg.connect(**(postgres | {'user': 'native_runtime'})) as database:
                    database.execute('SELECT * FROM app.native_jobs')
            except psycopg.errors.InsufficientPrivilege:
                check('worker-cannot-access-lifecycle-database', True)
            else:
                raise AssertionError('worker_cross_owner_access')
            provision = next(g for g in effects.grants if g['stage'] == 'provision')
            try:
                await asyncio.to_thread(transport.execute, provision)
            except Rejected:
                check('duplicate-tls-submission-is-held', len(calls['applies']) == 2)
            else:
                raise AssertionError('native_effect_repeated')
        finally:
            effects.release.set()
            for handle in handles:
                try:
                    await handle.cancel()
                except Exception:
                    pass
            executor.shutdown(wait=True)

    try:
        with native_wire(control, owners, initial, postgres, tmp_path / 'native-wire') as wire:
            transport, calls, worker_connect = wire
            asyncio.run(scenario())
    finally:
        Path(os.environ['P07_DISPATCH_OBSERVATIONS']).write_text(json.dumps({
            'checks': checks, 'histories': histories, 'native_platforms_tested': [],
            'native_write_authorized': False, 'owner_and_effect_observations': 'synthetic',
            'internal_effect_and_boundary_transport': 'actual_tls',
            'worker_journal': 'actual_owner_separated_postgresql',
        }, indent=2)+'\n')
