#!/usr/bin/env python3
"""One retained VM power transition, durable task binding and read-only recovery."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import sys
import time

from hosting_resources import SOURCE_ROOT
ROOT = SOURCE_ROOT
from provisioner.execution import readback_core as c
from provisioner.execution import execution_journal as journal
from provisioner.execution import vsphere_observe as vm
from provisioner.execution import vsphere_task_observe as task
from provisioner.execution.source_integrity import verify, verify_runtime
from provisioner.execution.run_files import current_window, encoded, load_private, require
from provisioner.execution.vsphere_history import CollectorClient

FORMAT = 'hosting-vsphere-power/1'
COMPLETE = 'POWER_CHANGED_REQUIRES_NATIVE_ACCEPTANCE'


def validate(request):
    c.exact_keys(request, {'format', 'source_commit', 'generation', 'snapshot', 'desired_power', 'task_manager_id'})
    require(request['format'] == FORMAT and isinstance(request['source_commit'], str)
            and re.fullmatch(r'[0-9a-f]{40}', request['source_commit']), 'Exact power source revision required')
    require(type(request['generation']) is int and request['generation'] > 0, 'Positive power generation required')
    vm.validate(request['snapshot'])
    require(request['snapshot']['contact_enabled'] is True and len(request['snapshot']['resources']) == 1,
            'Power transition requires one explicitly enabled VM')
    c.identifier(request['task_manager_id'])
    resource = request['snapshot']['resources'][0]
    runtime = resource['expected']['runtime']
    require(runtime['faultToleranceState'] == 'notConfigured', 'Fault-tolerant VMs require a separate lifecycle owner')
    require(request['desired_power'] in {'poweredOn', 'poweredOff'}
            and request['desired_power'] != runtime['powerState'], 'Exact opposite power transition required')
    return resource


def authorize(request, authority, *, resume=False):
    c.exact_keys(authority, {'format', 'request_sha256', 'valid_from', 'valid_until', 'change_ref',
                             'writer_fence_ref', 'containment_ref', 'placement_ref', 'data_quiesce_ref'})
    require(authority['format'] == 'hosting-vsphere-power-authority/1'
            and authority['request_sha256'] == c.digest(request), 'Power authority differs from exact request')
    for key in ('change_ref', 'writer_fence_ref', 'containment_ref', 'placement_ref'): c.text(authority[key])
    if request['desired_power'] == 'poweredOff': c.text(authority['data_quiesce_ref'])
    else: require(authority['data_quiesce_ref'] is None, 'Unexpected shutdown authority')
    current_window(authority)


class Client(CollectorClient):
    def __init__(self, request, session, ca_file=None):
        resource = validate(request)
        super().__init__(request['snapshot']['origin'], request['snapshot']['origin'], session,
                         vm.targets(request['snapshot']), request['task_manager_id'], ca_file)
        self.resource = resource
        self.desired = request['desired_power']
        self.request_sha256 = c.digest(request)

    def power(self):
        method = 'PowerOnVM_Task' if self.desired == 'poweredOn' else 'PowerOffVM_Task'
        payload = {'host': self.resource['expected']['runtime']['host']} if self.desired == 'poweredOn' else None
        result, _ = self._request('POST', vm.resource_target(self.resource, method), payload)
        vm.reference(result, 'Task', 'task')
        return result['value']

    def task_info(self, identifier):
        vm.moid(identifier, 'task')
        result, _ = self._request('GET', task.task_target({'moid': identifier}))
        return task.task_witness(result)

    def activity(self, since):
        entity = {'entity': {'type': 'VirtualMachine', 'value': self.resource['moid']}, 'recursion': 'self'}
        pending = self._collect({'entity': entity, 'state': ['queued', 'running']})
        completed = self._collect({'entity': entity, 'state': ['success', 'error'],
                                   'time': {'timeType': 'completedTime', 'beginTime': since}})
        return [task.task_witness(row) for row in pending + completed]


def attempt_state(events):
    """Reject reordered, orphan, rebound or post-completion task records."""
    attempts = []
    for event in events:
        kind, data = event['kind'], event['data']
        if kind == 'STARTED':
            require(not attempts or attempts[-1]['complete'] is not None, 'Earlier power outcome remains uncertain')
            c.exact_keys(data, {'request', 'authority_sha256'})
            validate(data['request'])
            require(isinstance(data['authority_sha256'], str) and c.HEX.fullmatch(data['authority_sha256']), 'Invalid authority digest')
            require(all(c.digest(p['request']) != c.digest(data['request']) for p in attempts), 'Power request was repeated')
            if attempts:
                require(data['request']['generation'] > attempts[-1]['request']['generation'], 'Power generation must increase')
            attempts.append(dict(request=data['request'], started_at=event['at'], started_event_sha256=c.digest(event),
                                 task_id=None, binding=None, complete=None))
        else:
            require(attempts and attempts[-1]['complete'] is None, 'Orphan or post-completion power event')
            state = attempts[-1]
            if kind in {'TASK_RETURNED','TASK_RECONCILED'}:
                c.exact_keys(data, {'task_id'} if kind=='TASK_RETURNED' else {'task_id','claim_sha256'})
                vm.moid(data['task_id'], 'task')
                if kind=='TASK_RECONCILED':
                    require(isinstance(data['claim_sha256'],str) and c.HEX.fullmatch(data['claim_sha256']), 'Invalid native reconciliation digest')
                require(state['task_id'] is None, 'Native task binding cannot change')
                state['task_id'] = data['task_id']
            elif kind == 'TASK_BOUND':
                c.exact_keys(data, {'record'})
                require(state['task_id'] is not None and state['binding'] is None, 'Unexpected task identity binding')
                validate_binding(state, data['record'])
                state['binding'] = data['record']
            elif kind == 'COMPLETED':
                require(state['binding'] is not None, 'Missing native task binding')
                validate_completion(state, data)
                state['complete'] = data
            elif kind=='OBSERVATION_AUTHORIZED':
                c.exact_keys(data,{'authority_sha256'})
                require(isinstance(data['authority_sha256'],str) and c.HEX.fullmatch(data['authority_sha256']), 'Invalid observation authority digest')
            else:
                raise ValueError('Unknown power execution event')
    return attempts


def reconcile_task(request,authority,claim,ledger,client,root=ROOT):
    """Attach an independently accepted lost-response task; issue no native write."""
    resource=validate(request); authorize(request,authority,resume=True)
    require(isinstance(root,Path) and verify_runtime(root)['status']=='RUNTIME_SOURCES_MATCH',
            'Exact runtime and explicitly selected source checkout required')
    source=verify(root)
    require(source['status']=='HASHES_MATCH' and source['commit']==request['source_commit'],'Exact clean recovery source required')
    require(client.request_sha256==c.digest(request),'Foreign power observation transport')
    c.exact_keys(claim,{'format','request_sha256','started_event_sha256','task_id','valid_from','valid_until',
                        'task_mapping_ref','writer_fence_ref','containment_ref'})
    require(claim['format']=='hosting-vsphere-power-reconciliation/1' and claim['request_sha256']==c.digest(request),
            'Native reconciliation differs from the held request')
    for key in ('task_mapping_ref','writer_fence_ref','containment_ref'): c.text(claim[key])
    vm.moid(claim['task_id'],'task'); current_window(claim)
    scope=dict(owner='vsphere-power',origin=request['snapshot']['origin'],vm_moid=resource['moid'])
    with journal.locked(ledger,scope) as log:
        attempts=attempt_state(log.events)
        require(attempts and c.digest(attempts[-1]['request'])==c.digest(request),'No matching held native power request')
        state=attempts[-1]
        require(state['task_id'] is None and state['complete'] is None
                and claim['started_event_sha256']==state['started_event_sha256'],'Reconciliation does not bind the exact unassigned attempt')
        client.deadline=min(client.deadline,time.monotonic()+min((c.timestamp(x['valid_until'])-c.timestamp(c.now())).total_seconds()
                            for x in (claim,authority)))
        witness=client.task_info(claim['task_id'])
        record=dict(moid=claim['task_id'],vm_moid=resource['moid'],description_id=witness.get('descriptionId'),
                    queued_at=witness.get('queueTime'),event_chain_id=witness.get('eventChainId'))
        validate_binding(state|{'task_id':claim['task_id']},record)
        observed=task.evaluate_task(record,witness)
        require(observed['identity_match'] and observed['progress'] in {'PENDING','COMPLETE'},'Native task mapping is failed or uncertain')
        current_window(claim); current_window(authority)
        # The claim comes from the independent native recovery owner, not a
        # "latest matching task" search or inference from matching power state.
        log.append('TASK_RECONCILED',{'task_id':claim['task_id'],'claim_sha256':c.digest(claim)})
        log.append('TASK_BOUND',{'record':record})
    return {'status':'TASK_BOUND_FOR_READ_ONLY_RESUME','native_acceptance':False,'production_activation':False}


def validate_binding(state, record):
    resource = validate(state['request'])
    task.validate_records([record], {resource['moid']})
    require(record['moid'] == state['task_id'] and record['description_id'] == (
        'VirtualMachine.powerOn' if state['request']['desired_power'] == 'poweredOn' else 'VirtualMachine.powerOff'),
        'Native power task differs')
    require(c.timestamp(state['started_at']) <= c.timestamp(record['queued_at']), 'Task predates this power attempt')


def normalize_after(request, observed):
    expected = deepcopy(validate(request)['expected'])
    expected['runtime']['powerState'] = request['desired_power']
    # A power task can increment changeVersion; it cannot change retained hardware.
    expected['config']['changeVersion'] = observed.get('config', {}).get('changeVersion')
    c.text(expected['config']['changeVersion'])
    for device in expected['config']['hardware']['device']:
        if device['_typeName'] == 'VirtualVmxnet3':
            device['connectable']['connected'] = request['desired_power'] == 'poweredOn' and device['connectable']['startConnected']
    return expected


def validate_completion(state, result):
    c.exact_keys(result, {'status', 'request_sha256', 'task_witness', 'snapshot', 'native_acceptance', 'production_activation'})
    require(result['status'] == COMPLETE and result['request_sha256'] == c.digest(state['request'])
            and result['native_acceptance'] is False and result['production_activation'] is False,
            'Power completion authority differs')
    require(task.evaluate_task(state['binding'], result['task_witness'])['task_completion_observed'], 'Power task is not complete')
    require(not c.differences(result['snapshot'], normalize_after(state['request'], result['snapshot'])),
            'Retained VM differs after power transition')


def observe_completion(request, state, client):
    record = state['binding']
    first_task = client.task_info(state['task_id'])
    outcome = task.evaluate_task(record, first_task)
    require(outcome['task_completion_observed'], 'Power task is pending, failed or uncertain; resume observation only')
    resource = validate(request)
    # Keep complete device inventory and unexpected-runtime-question checks.
    snapshots = []
    for _ in range(2):
        observed, mismatches = vm.snapshot(resource, client)
        require('/runtime/question:execution_blocked' not in mismatches, 'VM has an unanswered native question')
        expected = normalize_after(request, observed)
        require(not c.differences(observed, expected), 'Retained VM or power state differs after execution')
        snapshots.append(observed)
    require(snapshots[0] == snapshots[1], 'VM changed during power observation')
    activity = client.activity(state['started_at'])
    require(len(activity) == 1 and activity[0] == first_task, 'Unlisted, missing or changing VM task activity')
    last_task = client.task_info(state['task_id'])
    require(first_task == last_task, 'Power task changed during observation')
    return dict(status=COMPLETE, request_sha256=c.digest(request), task_witness=last_task,
                snapshot=snapshots[-1], native_acceptance=False, production_activation=False)


def execute(request, authority, ledger, client, *, execute_approved_change=False, resume=False, root=ROOT):
    resource = validate(request)
    authorize(request, authority, resume=resume)
    require(isinstance(root,Path) and verify_runtime(root)['status']=='RUNTIME_SOURCES_MATCH',
            'Exact runtime and explicitly selected source checkout required')
    source = verify(root)
    require(source['status'] == 'HASHES_MATCH' and source['commit'] == request['source_commit'], 'Exact clean power source required')
    require(resume or execute_approved_change is True, 'Explicit power mutation opt-in required')
    require(client.request_sha256 == c.digest(request), 'Power transport is bound to another request')
    client.deadline = min(client.deadline, time.monotonic() +
        (c.timestamp(authority['valid_until']) - c.timestamp(c.now())).total_seconds())
    scope = dict(owner='vsphere-power', origin=request['snapshot']['origin'], vm_moid=resource['moid'])
    with journal.locked(ledger, scope) as log:
        attempts = attempt_state(log.events)
        require(all(dict(owner='vsphere-power', origin=p['request']['snapshot']['origin'],
                         vm_moid=validate(p['request'])['moid']) == scope for p in attempts), 'Power journal resource differs')
        same = [p for p in attempts if c.digest(p['request']) == c.digest(request)]
        if same:
            state = same[0]
            require(state is attempts[-1], 'A later power generation superseded this request')
            if state['complete'] is not None: return state['complete']
            require(resume, 'Power was attempted; resume observation only')
            log.append('OBSERVATION_AUTHORIZED',{'authority_sha256':c.digest(authority)})
        else:
            require(not resume and (not attempts or attempts[-1]['complete'] is not None), 'Unknown or held power attempt')
            require(not attempts or request['generation'] > attempts[-1]['request']['generation'], 'Power generation must increase')
            since = c.now()
            for _ in range(2):
                _, mismatch = vm.snapshot(resource, client)
                require(not mismatch, 'VM differs from the reviewed pre-power snapshot')
            require(not client.activity(since), 'VM has active or crossing native work')
            current_window(authority)
            client.deadline = min(client.deadline, time.monotonic() +
                (c.timestamp(authority['valid_until']) - c.timestamp(c.now())).total_seconds())
            log.append('STARTED', {'request': request, 'authority_sha256': c.digest(authority)})
            # Any interruption after STARTED is uncertain. Never retry this POST.
            identifier = client.power()
            log.append('TASK_RETURNED', {'task_id': identifier})
            state = attempt_state(log.events)[-1]
        require(state['task_id'] is not None, 'Power response was lost; independent task reconciliation required')
        if state['binding'] is None:
            witness = client.task_info(state['task_id'])
            record = dict(moid=state['task_id'], vm_moid=resource['moid'],
                          description_id=witness.get('descriptionId'), queued_at=witness.get('queueTime'),
                          event_chain_id=witness.get('eventChainId'))
            validate_binding(state, record)
            require(task.evaluate_task(record, witness)['identity_match'], 'Returned task does not bind this VM')
            log.append('TASK_BOUND', {'record': record})
            state['binding'] = record
        result = observe_completion(request, state, client)
        current_window(authority)
        log.append('COMPLETED', result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'authority', 'ledger'): parser.add_argument('--' + name, required=True)
    parser.add_argument('--ca-file')
    parser.add_argument('--reconcile-task',type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--execute-approved-change', action='store_true')
    mode.add_argument('--resume', action='store_true')
    parser.add_argument('--source-root',type=Path,default=ROOT)
    args = parser.parse_args()
    try:
        request, authority = load_private(args.request), load_private(args.authority)
        validate(request); authorize(request, authority, resume=args.resume)
        client = Client(request, os.environ.get('VCENTER_SESSION_TOKEN'), args.ca_file)
        if args.reconcile_task:
            require(args.resume,'Task reconciliation is available only in read-only resume mode')
            reconcile_task(request,authority,load_private(args.reconcile_task),args.ledger,client,root=args.source_root)
        result = execute(request, authority, args.ledger, client,
                         execute_approved_change=args.execute_approved_change, resume=args.resume,root=args.source_root)
        print(json.dumps({'status': result['status'], 'request_sha256': result['request_sha256']}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, c.ObservationError):
        print('Power execution held; retain the private journal and resume observation only.', file=sys.stderr)
        return 2


if __name__ == '__main__': raise SystemExit(main())
