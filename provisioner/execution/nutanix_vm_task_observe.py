"""Read-only AHV VM and recorded Prism task evidence; never fences or replays work.

This explicit profile composes VMM v4.2 VM snapshots with Prism v4.3 task reads.
The installed tuple must support both interfaces. No discovery or fallback occurs.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import sys
from provisioner.execution import readback_core as c
from provisioner.execution import nutanix_vm_observe as vm
from provisioner.execution import nutanix_task_tree as tree

PROFILE = 'nutanix-ahv-v4.2-prism-v4.3-task-tree'


def validate(m: dict) -> None:
    c.common_manifest(m, 'nutanix')
    if m['profile'] != PROFILE: raise ValueError('Wrong explicit AHV task profile')
    snapshot = deepcopy(m); snapshot.pop('task', None); snapshot['profile'] = vm.PROFILE
    vm.validate(snapshot)
    # A recorded VM operation may have no children. Network task-tree semantics
    # remain unchanged; this profile explicitly accepts 1-16 tasks.
    tree.validate_graph(m, minimum_tasks=1)


def targets(m: dict) -> set[str]:
    validate(m)
    return {vm.resource_target(r) for r in m['resources']} | {tree.target(n['ext_id']) for n in tree.specs(m)}


def sample(m: dict, client) -> list[dict]:
    states = tree.sample_graph(m, client, vm.sample)
    for state in states:
        state['task_completion_observed'] = state['progress'] == 'COMPLETE'
    return states


def validate_observation_history(m: dict, history: list[dict], states: list[dict], current=None) -> None:
    tree.validate_history(m, history, states, current)
    for state in states:
        if state.get('resource_key') == 'scope': continue
        if state.get('task_completion_observed') is not (state.get('progress') == 'COMPLETE'):
            raise c.ObservationError('VM_TASK_COMPLETION_WITNESS_INVALID')


if __name__ == '__main__':
    import sys
    from provisioner.execution.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'NUTANIX'))
