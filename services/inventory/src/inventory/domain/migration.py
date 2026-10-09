"""Common destination review routing; platform modules validate native semantics."""

from typing import Any

from inventory.domain.ahv import destination_input as ahv_destination
from inventory.domain.discovery import Rejected, shape
from inventory.domain.destination_security import (
    require_matching_openstack_rules,
    select_security_mappings,
    source_security_ids,
    validate_security_flow_choices,
)
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
            # Preserve an incomplete review as a draft, without accepting
            # any invented destination policy. Review holds confirmation.
            if selected is not None:
                draft = shape(selected, {"platform", "project_id", "security_mappings", "flow_mappings"} if isinstance(selected, dict) and "flow_mappings" in selected else {"platform", "project_id", "security_mappings"})
                if (
                    draft["platform"] != "openstack"
                    or draft["project_id"] != target["project_id"]
                    or draft["security_mappings"] != []
                    or draft.get("flow_mappings", []) != []
                ):
                    raise Rejected("source_security_policy_observation_required")
            return
        if not source_ids and selected is None:
            return
        d = shape(selected, {"platform", "project_id", "security_mappings", "flow_mappings"} if "flow_mappings" in selected else {"platform", "project_id", "security_mappings"})
        if d["platform"] != "openstack" or d["project_id"] != target["project_id"]:
            raise Rejected("foreign_openstack_destination", 403)
        select_security_mappings(
            d["security_mappings"], source_ids,
            {g["id"] for g in target["security_groups"]},
        )
        if source_ids:
            require_matching_openstack_rules(source, d["security_mappings"], target)
            validate_security_flow_choices(source, target, d["security_mappings"], d.get("flow_mappings"))
    else:
        raise Rejected("supported_target_required")
