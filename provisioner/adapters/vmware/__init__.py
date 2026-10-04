"""VMware/NSX realization boundary.

The vCenter placement identity and the NSX network identity are deliberately
separate: a vSphere workload cannot be compiled until an observed NSX segment has
been explicitly mapped to it.
"""
from __future__ import annotations

from provisioner.adapters.base import (Adapter, WorkloadLifecycle,
                                       WorkloadLifecycleMode, _adapter)

LIMITS = (
    'VMware/NSX product tuple is unselected in the capability registry',
    'Workload compilation requires an explicit observed NSX segment mapping',
    'The security edge owns the isolated upstream route',
)


#: The vSphere module attaches a workload to the observed NSX quarantine segment and
#: declares no field for the workload's own portable address, so the address is realized
#: by that segment rather than dropped.
REALIZATION_NOTE = ('the workload is realized on the observed NSX quarantine segment instead')


WORKLOAD_LIFECYCLE = WorkloadLifecycle(WorkloadLifecycleMode.PER_MEMBER_OWNER, 'vsphere_power')

def adapter() -> Adapter:
    return _adapter('vmware', 'nsx-route', LIMITS, REALIZATION_NOTE,
                    workload_lifecycle=WORKLOAD_LIFECYCLE)
