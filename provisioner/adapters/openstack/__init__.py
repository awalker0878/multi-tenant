"""OpenStack realization boundary.

OpenStack is a distribution-specific realization, not a generic label: the
selected distribution, backend and mandatory network mutation policy are owner
decisions recorded outside this repository.
"""
from __future__ import annotations

from provisioner.adapters.base import (Adapter, WorkloadLifecycle,
                                       WorkloadLifecycleMode, _adapter)

LIMITS = (
    'OpenStack product tuple is unselected in the capability registry',
    'The actual distribution and backend remain an owner decision',
    'Mandatory network mutation policy is enforced by the platform owner',
)


WORKLOAD_LIFECYCLE = WorkloadLifecycle(WorkloadLifecycleMode.SAVED_PLAN, 'terraform_apply')

def adapter() -> Adapter:
    return _adapter('openstack', 'openstack-route', LIMITS,
                    workload_lifecycle=WORKLOAD_LIFECYCLE)
