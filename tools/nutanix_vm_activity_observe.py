#!/usr/bin/env python3
"""Bounded visible AHV task activity; never supplies writer exclusion or recovery authority.

Wire contract: Nutanix prism-go-client/v4.3.1 TasksApi.ListTasks and its
ListTasksRequest / ApiResponseMetadata models. Exact filter support, ordering,
count semantics and RBAC completeness require installed-target qualification.
"""
from copy import deepcopy
from pathlib import Path
import sys
if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provisioner.execution import readback_core as c
from tools import nutanix_vm_task_observe as task, nutanix_entity_activity as activity
from provisioner.execution.run_files import require

PROFILE = 'nutanix-ahv-v4.2-prism-v4.3-vm-task-activity'
# Preserve the AHV adapter's public query interface and report vocabulary.
from tools.nutanix_entity_activity import KEY, PAGE_SIZE, MAX_PAGES, MAX_RECORDS, FIELDS, target, observation_keys


def task_manifest(m):
    result = deepcopy(m); result['profile'] = task.PROFILE
    return result


def validate(m):
    require(m.get('profile') == PROFILE, 'Explicit AHV activity profile required')
    task.validate(task_manifest(m))
    require(c.timestamp(m['task']['created_before']) <= c.timestamp(c.now()), 'Task window must end before observation')


def targets(m):
    validate(m)
    return task.targets(task_manifest(m)) | {target(m, r['ext_id'], page) for r in m['resources'] for page in range(MAX_PAGES)}


def read_activity(m, client):
    return activity.read_activity(m, client, error_code='AHV_ACTIVITY_PAGE_UNKNOWN')


def activity_state(m, evidence, states, current=None):
    return activity.activity_state(m, evidence, states, current,
        reason='VISIBLE_VM_ACTIVITY_ONLY_NOT_NATIVE_WRITER_EXCLUSION')


def sample(m, client):
    before = read_activity(m, client); states = task.sample(m, client); after = read_activity(m, client)
    return states + [activity_state(m, dict(before=before, after=after), states)]


def validate_observation_history(m, history, states, current=None):
    if len(states) == 1 and states[0].get('resource_key') == 'scope':
        task.validate_observation_history(m, history, states, current); return
    try:
        require(len(states) == len(m['resources'])+1 and states[-1].get('resource_key') == KEY, 'Activity coverage missing')
        task.validate_observation_history(m, history, states[:-1], current)
        require(c.digest(states[-1]) == c.digest(activity_state(m, states[-1]['activity_witness'], states[:-1], current)),
                'Activity witness or summary differs')
    except (ValueError, TypeError, KeyError, IndexError):
        raise c.ObservationError('AHV_ACTIVITY_WITNESS_INVALID') from None


if __name__ == '__main__':
    from tools.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'NUTANIX'))
