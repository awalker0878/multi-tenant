#!/usr/bin/env python3
"""Exact Flow policies with recorded Prism tasks and bounded visible activity.

Neither task success nor absence of visible extra activity proves enforcement,
RBAC completeness, writer exclusion, or permission to resume a held attempt.
"""
from copy import deepcopy
from pathlib import Path
import sys
if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import readback_core as c, nutanix_flow_observe as flow, nutanix_task_tree as tree
from tools import nutanix_entity_activity as activity
from tools.run_files import require

PROFILE = 'nutanix-microseg-v4.2-prism-v4.3-policy-task-activity'


def validate(m):
    require(m.get('profile') == PROFILE, 'Explicit Flow activity profile required')
    snapshot = deepcopy(m); snapshot.pop('task', None); snapshot['profile'] = flow.PROFILE
    flow.validate(snapshot); tree.validate_graph(m, minimum_tasks=1)
    require(c.timestamp(m['task']['created_before']) <= c.timestamp(c.now()), 'Task window must end before observation')


def targets(m):
    validate(m)
    return ({flow.resource_target(r) for r in m['resources']}
            | {tree.target(n['ext_id']) for n in tree.specs(m)}
            | {activity.target(m, r['ext_id'], page) for r in m['resources'] for page in range(activity.MAX_PAGES)})


def observation_keys(m): return activity.observation_keys(m)


def activity_state(m, evidence, states, current=None):
    return activity.activity_state(m, evidence, states, current,
        reason='VISIBLE_POLICY_ACTIVITY_ONLY_NOT_NATIVE_WRITER_EXCLUSION')


def sample(m, client):
    before = activity.read_activity(m, client, error_code='FLOW_ACTIVITY_PAGE_UNKNOWN')
    states = tree.sample_graph(m, client, flow.sample)
    for state in states: state['task_completion_observed'] = state['progress'] == 'COMPLETE'
    after = activity.read_activity(m, client, error_code='FLOW_ACTIVITY_PAGE_UNKNOWN')
    return states + [activity_state(m, dict(before=before, after=after), states)]


def validate_observation_history(m, history, states, current=None):
    try:
        if len(states) == 1 and states[0].get('resource_key') == 'scope':
            tree.validate_history(m, history, states, current); return
        require(len(states) == len(m['resources'])+1 and states[-1].get('resource_key') == activity.KEY,
                'Policy activity coverage missing')
        policy_states = states[:-1]
        flow.validate_snapshot_witnesses(m, policy_states)
        tree.validate_history(m, history, policy_states, current)
        for state in policy_states:
            require(state.get('task_completion_observed') is (state.get('progress') == 'COMPLETE'),
                    'Task completion contradicts recorded graph')
        require(c.digest(states[-1]) == c.digest(activity_state(m, states[-1]['activity_witness'], policy_states, current)),
                'Policy activity summary contradicts witness')
    except (ValueError, TypeError, KeyError, IndexError):
        raise c.ObservationError('FLOW_ACTIVITY_WITNESS_INVALID') from None


if __name__ == '__main__':
    from tools.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'NUTANIX'))
