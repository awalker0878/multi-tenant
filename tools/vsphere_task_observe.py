#!/usr/bin/env python3
"""Observe accepted vSphere task IDs with VM snapshots; never authorize replay."""
from pathlib import Path
import re
import sys
if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import readback_core as c, vsphere_observe as vm
from tools.run_files import require

PROFILE = 'vsphere-vi-json-8.0.3.0-vm-tasks'
OPERATIONS = {'VirtualMachine.powerOn', 'VirtualMachine.powerOff', 'VirtualMachine.reconfigVm'}
CLONE = 'VirtualMachine.clone'


def vm_manifest(m): return {key: (vm.PROFILE if key == 'profile' else value) for key, value in m.items() if key != 'task'}


def validate(m):
    c.common_manifest(m, 'vmware'); require(m['profile'] == PROFILE and 'task' in m, 'Explicit task profile required')
    vm.validate(vm_manifest(m)); task = m['task']; c.exact_keys(task, {'execution_record_ref', 'records'})
    c.text(task['execution_record_ref'])
    validate_records(task['records'], {r['moid'] for r in m['resources']})


def validate_records(records, vm_ids, *, clone_sources=None, ancestry=False):
    require(isinstance(records, list) and 1 <= len(records) <= 20, 'Enumerate 1-20 exact tasks')
    ids = set(); entities = set()
    for record in records:
        require(isinstance(record, dict), 'Task record object required')
        clone = record.get('description_id') == CLONE and clone_sources is not None
        keys = {'moid', 'vm_moid', 'description_id', 'queued_at', 'event_chain_id'}
        if ancestry: keys |= {'parent_task_id', 'root_task_id'}
        if clone: keys.add('source_moid')
        c.exact_keys(record, keys)
        vm.moid(record['moid'], 'task'); vm.moid(record['vm_moid'], 'vm')
        require(record['moid'] not in ids and (record['description_id'] in OPERATIONS or clone), 'Duplicate or unsupported task')
        if clone:
            vm.moid(record['source_moid'], 'vm')
            require(record['source_moid'] in clone_sources and record['source_moid'] != record['vm_moid'], 'Unbound clone source')
        require(type(record['event_chain_id']) is int and record['event_chain_id'] >= 0, 'Native event chain required')
        require(c.timestamp(record['queued_at']) <= c.timestamp(c.now()), 'Future task record refused')
        ids.add(record['moid']); entities.add(record['vm_moid'])
    require(entities == vm_ids, 'Tasks must cover exactly the observed VMs')


def task_target(record): return vm.PREFIX + 'Task/' + record['moid'] + '/info'


def targets(m):
    validate(m)
    return vm.targets(vm_manifest(m)) | {task_target(r) for r in m['task']['records']}


WITNESS_FIELDS = {'_typeName', 'key', 'task', 'entity', 'descriptionId', 'eventChainId', 'queueTime',
                  'startTime', 'completeTime', 'state', 'cancelled', 'parentTaskKey', 'rootTaskKey'}


def task_witness(body):
    witness = {key: body[key] for key in WITNESS_FIELDS if key in body}
    witness.update(has_error=body.get('error') is not None, has_result=body.get('result') is not None)
    try:
        for key, value in witness.items():
            if value is None: continue
            if key in {'task', 'entity'}:
                vm.reference(value, 'Task' if key == 'task' else 'VirtualMachine', 'task' if key == 'task' else 'vm')
            elif key in {'key', 'parentTaskKey', 'rootTaskKey'}:
                if value != '': vm.moid(value, 'task')
            elif key in {'queueTime', 'startTime', 'completeTime'}: c.timestamp(value)
            elif key == 'descriptionId': require(isinstance(value, str) and re.fullmatch(r'VirtualMachine\.[A-Za-z]{1,64}', value), 'Invalid task operation')
            elif key == '_typeName': require(value == 'TaskInfo', 'Invalid task type')
            elif key == 'state': require(value in {'queued', 'running', 'success', 'error'}, 'Unknown task state')
            elif key == 'eventChainId': require(type(value) is int and value >= 0, 'Invalid event chain')
            else: require(type(value) is bool, 'Invalid task flag')
    except (ValueError, TypeError):
        return {'has_error': False, 'has_result': False}
    if body.get('descriptionId') == CLONE and witness['has_result']:
        try:
            vm.reference(body['result'], 'VirtualMachine', 'vm')
            witness['result_reference'] = dict(body['result'])
        except (ValueError, TypeError):
            pass  # Preserve the unsupported-result flag without logging its contents.
    return witness


def evaluate_task(record, body, current=None):
    current = current or c.timestamp(c.now())
    result = dict(resource_key=record['moid'], identity_match=False, config_status='UNKNOWN', progress='UNKNOWN',
                  reason='VSPHERE_TASK_UNCERTAIN', task_completion_observed=False,
                  task_witness=body, config_sha256=c.digest(body), mismatch_fields=[])
    try:
        c.exact_keys(body, {'has_error', 'has_result'}, WITNESS_FIELDS | {'result_reference'})
        require(type(body['has_error']) is bool and type(body['has_result']) is bool, 'Typed native result flags required')
        require(body.get('_typeName') == 'TaskInfo' and body.get('key') == record['moid'], 'Wrong task identity')
        vm.reference(body.get('task'), 'Task', 'task'); vm.reference(body.get('entity'), 'VirtualMachine', 'vm')
        clone = record['description_id'] == CLONE
        entity = record['source_moid'] if clone else record['vm_moid']
        require(body['task']['value'] == record['moid'] and body['entity']['value'] == entity
                and body.get('descriptionId') == record['description_id']
                and type(body.get('eventChainId')) is int and body['eventChainId'] == record['event_chain_id']
                and c.timestamp(body['queueTime']) == c.timestamp(record['queued_at']), 'Task execution binding differs')
        require(type(body.get('cancelled')) is bool, 'Explicit cancellation state required')
        if 'parent_task_id' in record:
            require((body.get('parentTaskKey') or None) == record['parent_task_id'], 'Task parent differs')
            require(body.get('rootTaskKey') == record['root_task_id'] if record['parent_task_id'] else
                    body.get('rootTaskKey') in (None, '', record['moid']), 'Task root differs')
        else:
            require(not body.get('parentTaskKey') and body.get('rootTaskKey') in (None, '', record['moid']), 'Task tree requires separate reconciliation')
        state = body.get('state'); require(state in {'queued', 'running', 'success', 'error'}, 'Unknown task state')
        result.update(identity_match=True, config_status='MATCH', native_state=state)
        # Native error text and arbitrary task results never enter the journal.
        if body['cancelled'] or state == 'error':
            result.update(progress='FAILED', reason='VSPHERE_TASK_FAILED_OR_CANCELLED'); return result
        require(not body['has_error'], 'Contradictory native task error')
        if clone and state == 'success':
            require(body['has_result'], 'Completed clone result required')
            vm.reference(body.get('result_reference'), 'VirtualMachine', 'vm')
            require(body['result_reference']['value'] == record['vm_moid'], 'Clone destination differs')
        else:
            require(not body['has_result'] and 'result_reference' not in body, 'Contradictory or unsupported task result')
        if state in {'queued', 'running'}:
            require(body.get('completeTime') is None, 'Pending task claims completion')
            result.update(progress='PENDING', reason='VSPHERE_TASK_PENDING'); return result
        queued = c.timestamp(body['queueTime']); started = c.timestamp(body['startTime']); completed = c.timestamp(body['completeTime'])
        require(queued <= started <= completed <= current, 'Task completion chronology differs')
        result.update(progress='COMPLETE', reason='EXACT_TASK_COMPLETED_REPLAY_NOT_AUTHORIZED', task_completion_observed=True,
                      execution_sha256=c.digest({key: body[key] for key in ('key', 'descriptionId', 'entity', 'eventChainId', 'queueTime', 'startTime', 'completeTime')}))
        if clone:
            result['execution_sha256'] = c.digest({'task_sha256': result['execution_sha256'], 'result_reference': body['result_reference']})
    except (ValueError, TypeError, KeyError):
        result.update(config_status='UNKNOWN', progress='UNKNOWN')
    return result


def task_sample(record, client):
    body, _ = client.get(task_target(record))
    return evaluate_task(record, task_witness(body))


def sample(m, client):
    before = [task_sample(r, client) for r in m['task']['records']]
    snapshots = vm.sample(vm_manifest(m), client)
    after = [task_sample(r, client) for r in m['task']['records']]
    for first, last in zip(before, after):
        if first.get('native_state') in {'success', 'error'} and c.digest(first) != c.digest(last):
            raise c.ObservationError('VSPHERE_TERMINAL_TASK_CHANGED')
    return snapshots + after


def observation_keys(m):
    return {r['moid'] for r in m['resources']} | {r['moid'] for r in m['task']['records']}


def validate_observation_history(m, history, states, current=None):
    current = current or c.timestamp(c.now())
    if len(states) == 1 and states[0].get('resource_key') == 'scope': return
    vm_ids = {r['moid'] for r in m['resources']}
    vm.validate_observation_history(vm_manifest(m), history, [s for s in states if s.get('resource_key') in vm_ids], current)
    records = {r['moid']: r for r in m['task']['records']}
    for state in states:
        key = state.get('resource_key')
        if key in records:
            witness = state.get('task_witness')
            if not isinstance(witness, dict) or c.digest(state) != c.digest(evaluate_task(records[key], witness, current)):
                raise c.ObservationError('VSPHERE_TASK_WITNESS_DIFFERS')
    previous = {s['resource_key']: s for h in history for s in h['states'] if s.get('task_completion_observed') is True}
    for state in states:
        if state['resource_key'] in previous and c.digest(state) != c.digest(previous[state['resource_key']]):
            raise c.ObservationError('VSPHERE_TERMINAL_TASK_CHANGED')


if __name__ == '__main__':
    from tools.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'VCENTER', session=True))
