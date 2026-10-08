"""Common destination review routing; platform modules validate native semantics."""

from typing import Any

from inventory.domain.ahv import destination_input as ahv_destination
from inventory.domain.discovery import Rejected, shape
from inventory.domain.destination_security import select_security_mappings, source_security_ids
from inventory.domain.vmware import destination_input as vmware_destination


def destination_input(body: dict[str, Any], source: dict[str, Any], target: dict[str, Any]) -> None:
    platform = target["platform"]
    if platform == "ahv":
        ahv_destination(body, source, target)
    elif platform == "vmware":
        vmware_destination(body, source, target)
    elif platform == "openstack":
        # Resource/placement allocations still belong to Planning. A Neutron
        # security choice may only refer to project-scoped target API records.
        source_ids = source_security_ids(source)
        selected = body.get("destination")
        if source_ids is None:
            raise Rejected("source_security_policy_observation_required")
        if not source_ids and selected is None:
            return
        d = shape(selected, {"platform", "project_id", "security_mappings"})
        if d["platform"] != "openstack" or d["project_id"] != target["project_id"]:
            raise Rejected("foreign_openstack_destination", 403)
        select_security_mappings(
            d["security_mappings"], source_ids,
            {g["id"] for g in target["security_groups"]},
        )
    else:
        raise Rejected("supported_target_required")
