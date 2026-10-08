"""Common destination review routing; platform modules validate native semantics."""

from typing import Any

from inventory.domain.ahv import destination_input as ahv_destination
from inventory.domain.discovery import Rejected
from inventory.domain.vmware import destination_input as vmware_destination


def destination_input(body: dict[str, Any], source: dict[str, Any], target: dict[str, Any]) -> None:
    platform = target["platform"]
    if platform == "ahv":
        ahv_destination(body, source, target)
    elif platform == "vmware":
        vmware_destination(body, source, target)
    elif platform == "openstack":
        # OpenStack allocations are bound by the existing Planning resource mapping.
        if body.get("destination") is not None:
            raise Rejected("unexpected_destination_mapping")
    else:
        raise Rejected("supported_target_required")
