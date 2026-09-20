#!/usr/bin/env python3
"""Observe accepted vSphere task IDs with VM snapshots; never authorize replay."""
from pathlib import Path
import sys
if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import readback_core as c, vsphere_observe as vm
from tools.run_files import require

PROFILE = 'vsphere-vi-json-8.0.3.0-vm-tasks'
OPERATIONS = {'VirtualMachine.powerOn', 'VirtualMachine.powerOff', 'VirtualMachine.reconfigVm'}


def vm_manifest(m): return {key: (vm.PROFILE if key == 'profile' else value) for key, value in m.items() if key != 'task'}


def validate(m):
    c.common_manifest(m, 'vmware'); require(m['profile'] == PROFILE and 'task' in m, 'Explicit task profile required')
    vm.validate(vm_manifest(m)); task = m['task']; c.exact_keys(task, {'execution_record_ref', 'records'})
    c.text(task['execution_record_ref'])
    require(isinstance(task['records'], list) and 1 <= len(task['records']) <= 20, 'Enumerate 1-20 exact tasks')
    ids = set(); entities = set()
    for record in task['records']:
        c.exact_keys(record, {'moid', 'vm_moid', 'description_id', 'queued_at', 'event_chain_id'})
        vm.moid(record['moid'], 'task'); vm.moid(record['vm_moid'], 'vm')
        require(record['moid'] not in ids and record['description_id'] in OPERATIONS, 'Duplicate or unsupported task')
        require(type(record['event_chain_id']) is int and record['event_chain_id'] >= 0, 'Native event chain required')
        require(c.timestamp(record['queued_at']) <= c.timestamp(c.now()), 'Future task record refused')
        ids.add(record['moid']); entities.add(record['vm_moid'])
    require(entities == {r['moid'] for r in m['resources']}, 'Tasks must cover exactly the observed VMs')


def task_target(record): return vm.PREFIX + 'Task/' + record['moid'] + '/info'


def targets(m):
    validate(m)
    return vm.targets(vm_manifest(m)) | {task_target(r) for r in m['task']['records']}


def task_sample(record, client):
    body, _ = client.get(task_target(record))
    result = dict(resource_key=record['moid'], identity_match=False, config_status='UNKNOWN', progress='UNKNOWN',
                  reason='VSPHERE_TASK_UNCERTAIN', task_completion_observed=False)
    try:
        require(body.get('_typeName') == 'TaskInfo' and body.get('key') == record['moid'], 'Wrong task identity')
        vm.reference(body.get('task'), 'Task', 'task'); vm.reference(body.get('entity'), 'VirtualMachine', 'vm')
        require(body['task']['value'] == record['moid'] and body['entity']['value'] == record['vm_moid']
                and body.get('descriptionId') == record['description_id']
                and type(body.get('eventChainId')) is int and body['eventChainId'] == record['event_chain_id']
                and c.timestamp(body['queueTime']) == c.timestamp(record['queued_at']), 'Task execution binding differs')
        require(type(body.get('cancelled')) is bool, 'Explicit cancellation state required')
        require(not body.get('parentTaskKey') and body.get('rootTaskKey') in (None, '', record['moid']), 'Task tree requires separate reconciliation')
        state = body.get('state'); require(state in {'queued', 'running', 'success', 'error'}, 'Unknown task state')
        result.update(identity_match=True, config_status='MATCH', native_state=state)
        # Native error text and arbitrary task results never enter the journal.
        if body['cancelled'] or state == 'error':
            result.update(progress='FAILED', reason='VSPHERE_TASK_FAILED_OR_CANCELLED'); return result
        require(body.get('error') is None and body.get('result') is None, 'Contradictory or unsupported task result')
        if state in {'queued', 'running'}:
            require(body.get('completeTime') is None, 'Pending task claims completion')
            result.update(progress='PENDING', reason='VSPHERE_TASK_PENDING'); return result
        queued = c.timestamp(body['queueTime']); started = c.timestamp(body['startTime']); completed = c.timestamp(body['completeTime'])
        require(queued <= started <= completed <= c.timestamp(c.now()), 'Task completion chronology differs')
        result.update(progress='COMPLETE', reason='EXACT_TASK_COMPLETED_REPLAY_NOT_AUTHORIZED', task_completion_observed=True,
                      execution_sha256=c.digest({key: body[key] for key in ('key', 'descriptionId', 'entity', 'eventChainId', 'queueTime', 'startTime', 'completeTime')}))
    except (ValueError, TypeError, KeyError):
        result.update(config_status='UNKNOWN', progress='UNKNOWN')
    return result


def sample(m, client):
    before = [task_sample(r, client) for r in m['task']['records']]
    snapshots = vm.sample(vm_manifest(m), client)
    after = [task_sample(r, client) for r in m['task']['records']]
    for first, last in zip(before, after):
        if first.get('native_state') in {'success', 'error'} and c.digest(first) != c.digest(last):
            raise c.ObservationError('VSPHERE_TERMINAL_TASK_CHANGED')
    return snapshots + after


def validate_observation_history(m, history, states):
    previous = {s['resource_key']: s for h in history for s in h['states'] if s.get('task_completion_observed') is True}
    for state in states:
        if state['resource_key'] in previous and c.digest(state) != c.digest(previous[state['resource_key']]):
            raise c.ObservationError('VSPHERE_TERMINAL_TASK_CHANGED')


if __name__ == '__main__':
    from tools.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'VCENTER', session=True))
