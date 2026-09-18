"""Scripted small task tree over the existing real loopback HTTPS fixture.

Task operation names, IDs and API bodies are synthetic. No native behaviour,
writer fence, platform qualification or operational authority is demonstrated.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from lab.native_readback_fixture import manifest as single, VPC, TASK, TENANT
from tools import nutanix_observe as native, nutanix_task_tree as tree

SUBNET = '44444444-4444-4444-8444-444444444444'
CHILD_A = 'ZXJnb24=:55555555-5555-4555-8555-555555555555'
CHILD_B = 'ZXJnb24=:66666666-6666-4666-8666-666666666666'
GRANDCHILD = 'ZXJnb24=:77777777-7777-4777-8777-777777777777'


def manifest(origin: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    m = single('nutanix', origin); m['profile'] = tree.PROFILE
    m['operation_id'] = 'fixture-task-tree-01'
    m['resources'].append({'kind': 'subnet', 'ext_id': SUBNET, 'expected_etag': '"fixture-subnet-1"',
        'expected': {'extId': SUBNET, '$objectType': 'networking.v4.config.Subnet', 'tenantId': TENANT,
                     'name': 'fixture-subnet', 'subnetType': 'OVERLAY', 'vpcReference': VPC,
                     'isExternal': False, 'isNatEnabled': False, 'ipConfig': []}})
    m['task'] = {'ext_id': TASK, 'operation': 'Fixture create domain',
        'created_after': (now - timedelta(seconds=120)).isoformat(),
        'created_before': (now - timedelta(seconds=5)).isoformat(), 'entity_ids': [VPC, SUBNET],
        'descendants': [
            {'ext_id': CHILD_A, 'parent_ext_id': TASK, 'operation': 'Fixture allocate VPC', 'entity_ids': [VPC]},
            {'ext_id': CHILD_B, 'parent_ext_id': TASK, 'operation': 'Fixture allocate subnet', 'entity_ids': [SUBNET]},
            {'ext_id': GRANDCHILD, 'parent_ext_id': CHILD_A, 'operation': 'Fixture validate VPC', 'entity_ids': [VPC]}]}
    return m


def responses(m: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    result = {native.resource_target(r): {'status': 200, 'etag': r['expected_etag'],
              'body': {'data': deepcopy(r['expected'])}} for r in m['resources']}
    age = {TASK: (90, 10), CHILD_A: (85, 20), CHILD_B: (80, 18), GRANDCHILD: (75, 30)}
    for spec in tree.specs(m):
        ident = spec['ext_id']; created, complete = age[ident]
        children = tree.children(m, ident)
        data = {'$objectType': 'prism.v4.config.Task', 'extId': ident, 'operation': spec['operation'],
            'createdTime': (now - timedelta(seconds=created)).isoformat(),
            'completedTime': (now - timedelta(seconds=complete)).isoformat(), 'status': 'SUCCEEDED',
            'numberOfSubtasks': len(children), 'subTasks': [{'extId': x} for x in children],
            'numberOfEntitiesAffected': len(spec['entity_ids']),
            'entitiesAffected': [{'extId': x} for x in spec['entity_ids']],
            'rootTask': {'extId': TASK}, 'errorMessages': [], 'warnings': []}
        if spec['parent_ext_id']: data['parentTask'] = {'extId': spec['parent_ext_id']}
        result[tree.target(ident)] = {'status': 200, 'body': {'data': data}}
    return result


def reset(fixture):
    fixture.routes = {}; fixture.requests = []; fixture.counts = {}; fixture.hook = None
    now = datetime.now(timezone.utc); m = manifest(fixture.origin, now)
    fixture.routes = responses(m, now); return m
