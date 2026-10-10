"""One Inventory-owned native profile read-count contract.

Worker collectors still perform each GET and request an authority permit first.
Inventory owns admission and completion bounds, never allowing a collector to
invent a count that exceeds the enrolled endpoint budget.
"""
from typing import Any

from inventory.domain.source_profile import source_profile_read_count
from inventory.domain.discovery import Rejected


def bounds(platform: str, kind: str, max_pages: int,
           stream: dict[str, Any], profile: dict[str, Any] | None = None
           ) -> tuple[int, int]:
    if kind == "source_profile":
        if platform == "openstack":
            return (5, 101) if profile is None else (
                source_profile_read_count(profile), source_profile_read_count(profile)
            )
        fixed = {"vmware": 8, "ahv": 4}.get(platform)
        if fixed is not None:
            return fixed, fixed
    if kind == "target_profile":
        if platform == "openstack":
            # Image schema/import, Nova flavors, Cinder types, Neutron
            # extensions/SGs and two live microversion roots.
            return 8, 8
        if platform == "vmware":
            return (7, 50) if "nsx_policy" in stream else (6, 51)
        if platform == "ahv":
            maximum = 2 + 5 * min(max_pages, 10) + 11
            if profile is None:
                return 2, maximum
            minimum = 2 + sum(
                max(1, (len(profile[field]) + 99) // 100)
                for field in ("storage_containers", "subnets", "vpcs",
                              "categories", "policies")
            )
            return minimum, maximum
    raise Rejected("profile_read_manifest_unsupported")
