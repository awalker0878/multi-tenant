"""OpenStack profile completeness includes individually collected Neutron groups."""

import pytest

from inventory.domain.discovery import Rejected
from inventory.domain.source_profile import source_profile_read_count


def profile(groups: list[str], volumes: int = 0) -> dict:
    return {
        "platform": "openstack", "schema_version": 3,
        "native": {
            "disk_records": [
                {"role": "root"},
                *({"role": "data_volume"} for _ in range(volumes)),
            ],
            "metadata": {
                "ports": [{"security_groups": groups}],
                "security_groups": [{"id": item} for item in groups],
            },
        },
    }


def test_security_group_reads_are_counted() -> None:
    assert source_profile_read_count(profile([])) == 5
    assert source_profile_read_count(profile(["sg-a", "sg-b"], 1)) == 8


@pytest.mark.parametrize("groups,observed", [
    (["sg-a"], []), (["sg-a", "sg-a"], [{"id": "sg-a"}]),
])
def test_incomplete_group_collection_fails_closed(groups: list[str], observed: list[dict]) -> None:
    value = profile(groups)
    value["native"]["metadata"]["security_groups"] = observed
    with pytest.raises(Rejected, match="source_profile_security_collection_incomplete"):
        source_profile_read_count(value)


def test_unknown_port_group_membership_does_not_claim_empty_rules() -> None:
    value = profile([])
    value["native"]["metadata"]["ports"] = [{"security_groups": None}]
    assert source_profile_read_count(value) == 5


def test_bounded_maximum_profile_reads_matches_native_collector() -> None:
    # OpenStack collector caps attached volumes at 32 and unique SGs at 64.
    assert source_profile_read_count(profile([f"sg-{i}" for i in range(64)], 32)) == 101
    with pytest.raises(Rejected, match="collection_bound_exceeded"):
        source_profile_read_count(profile([f"sg-{i}" for i in range(65)], 32))
