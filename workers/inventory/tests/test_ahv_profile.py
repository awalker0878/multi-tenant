"""AHV profiles retain scoped API facts, completeness and qualification boundaries."""

from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from inventory_worker.infrastructure.ahv_profile import collect_ahv, complete_list
from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.profile_collection import collect_profile


def uid() -> str:
    return str(uuid4())


def test_seven_budgeted_reads_use_pinned_origin_and_scope() -> None:
    project, cluster, pc, storage, subnet, foreign, shared = [uid() for _ in range(7)]
    stream = {
        "kind": "target_profile",
        "cluster_id": cluster,
        "prism_central_id": pc,
        "shared_resource_ids": [shared],
        "credential_file": "/secret",
        "base_url": "https://pc.invalid",
    }
    policy = {"platform": "ahv", "native_scope": project, "coverage_reference": "q08"}
    calls: list[str] = []
    budget: list[bool] = []

    def exchange(connection: dict[str, Any], path: str, headers: dict[str, str]) -> dict[str, Any]:
        assert connection is stream and headers == {"X-Ntnx-Api-Key": "secret"}
        assert len(budget) == len(calls) + 1
        calls.append(path)
        if "/clusters/" in path:
            return {
                "data": {
                    "extId": cluster,
                    "name": "AHV lab",
                    "config": {
                        "isAvailable": True,
                        "hypervisorTypes": ["AHV"],
                        "buildInfo": {"version": "7.6"},
                        "clusterSoftwareMap": [{"softwareType": "AHV", "version": "11.2"}],
                    },
                }
            }
        if "/domain-managers/" in path:
            return {
                "data": {
                    "extId": pc,
                    "config": {"buildInfo": {"version": "7.6"}, "credentials": ["never exposed"]},
                }
            }
        rows = []
        if "storage-containers" in path:
            rows = [
                {
                    "extId": storage,
                    "clusterExtId": cluster,
                    "name": "migrations",
                    "isMarkedForRemoval": False,
                    "isInternal": False,
                }
            ]
        if "/subnets" in path:
            rows = [
                {"extId": subnet, "projectExtId": project},
                {"extId": foreign, "projectExtId": uid()},
                {"extId": shared},
            ]
        return {"data": rows, "metadata": {"totalAvailableResults": len(rows)}}

    with (
        patch("inventory_worker.infrastructure.ahv_profile.exchange", side_effect=exchange),
        patch("inventory_worker.infrastructure.ahv_profile.secret", return_value="secret"),
    ):
        result = collect_profile(policy, stream, None, lambda: budget.append(True))
    profile = result["profile"]
    assert len(calls) == len(budget) == 7
    assert profile["platform"] == "ahv" and profile["schema_version"] == 2
    assert {s["extId"] for s in profile["subnets"]} == {subnet, shared}
    assert profile["native_qualification"] == "not_established"
    assert profile["inventory_complete"] is True and not profile["holds"]
    assert "never exposed" not in str(profile)
    assert profile["observations_sha256"] and result["terminal"] is True


@pytest.mark.parametrize(
    "fault", ["page", "total", "missing_total", "duplicate", "next", "wrong_type"]
)
def test_partial_or_ambiguous_discovery_is_never_a_complete_profile(fault: str) -> None:
    key = uid()
    document: dict[str, Any] = {"data": [{"extId": key}], "metadata": {"totalAvailableResults": 1}}
    if fault == "page":
        document["data"] = [{"extId": uid()} for _ in range(100)]
    if fault == "total":
        document["metadata"]["totalAvailableResults"] = 2
    if fault == "missing_total":
        document["metadata"] = {}
    if fault == "duplicate":
        document["data"].append({"extId": key})
    if fault == "next":
        document["metadata"]["links"] = [{"rel": "next", "href": "https://foreign.invalid"}]
    if fault == "wrong_type":
        document["data"] = ["invalid"]
    with pytest.raises(CollectionFailure):
        complete_list(document)


def test_foreign_prism_central_response_cannot_change_authority() -> None:
    stream = {"cluster_id": uid(), "prism_central_id": uid(), "credential_file": "/secret"}
    with (
        patch(
            "inventory_worker.infrastructure.ahv_profile.exchange",
            return_value={"data": {"extId": uid()}},
        ),
        patch("inventory_worker.infrastructure.ahv_profile.secret", return_value="secret"),
        pytest.raises(CollectionFailure),
    ):
        collect_ahv({"native_scope": uid()}, stream, 100, lambda: None)
