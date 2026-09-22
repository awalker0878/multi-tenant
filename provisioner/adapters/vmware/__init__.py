"""VMware/NSX realization boundary.

The vCenter placement identity and the NSX network identity are deliberately
separate: a vSphere workload cannot be compiled until an observed NSX segment has
been explicitly mapped to it.
"""
from __future__ import annotations

from provisioner.adapters.base import Adapter, _adapter

LIMITS = (
    'VMware/NSX product tuple is unselected in the capability registry',
    'Workload compilation requires an explicit observed NSX segment mapping',
    'The security edge owns the isolated upstream route',
)


def adapter() -> Adapter:
    return _adapter('vmware', 'nsx-route', LIMITS)