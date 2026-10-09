"""AHV profiles retain scoped API facts, completeness and qualification boundaries."""

from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from inventory_worker.infrastructure.ahv_profile import collect_ahv, collect_list
from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.profile_collection import collect_profile


def uid() -> str:
    return str(uuid4())


def test_ten_budgeted_reads_include_native_microseg_reference_catalogue() -> None:
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
    assert len(calls) == len(budget) == 10
    assert profile["platform"] == "ahv" and profile["schema_version"] == 2
    assert {s["extId"] for s in profile["subnets"]} == {subnet, shared}
    assert profile["native_qualification"] == "not_established"
    assert profile["inventory_complete"] is True and not profile["holds"]
    assert "never exposed" not in str(profile)
    assert profile["observations_sha256"] and result["terminal"] is True


@pytest.mark.parametrize("count", [0, 1, 100, 101, 200, 1000])
def test_numbered_pages_charge_each_request_and_never_follow_native_links(count: int) -> None:
    rows = [{"extId": uid()} for _ in range(count)]
    stream = {"credential_file": "/secret"}
    calls: list[str] = []
    budget: list[bool] = []

    def page(connection: dict[str, Any], route: str, headers: dict[str, str]) -> dict[str, Any]:
        assert connection is stream
        assert len(budget) == len(calls) + 1
        assert headers == {"X-Ntnx-Api-Key": "current"}
        index = len(calls)
        assert route == f"/api/prism/v4.3/config/categories?$limit=100&$page={index}"
        calls.append(route)
        return {
            "data": rows[index * 100 : (index + 1) * 100],
            "metadata": {
                "totalAvailableResults": count,
                "links": [{"rel": "next", "href": "https://untrusted.invalid/"}],
            },
        }

    with (
        patch("inventory_worker.infrastructure.ahv_profile.exchange", side_effect=page),
        patch(
            "inventory_worker.infrastructure.ahv_profile.secret", return_value="current"
        ) as secret,
    ):
        collected, observations = collect_list(
            stream, "/api/prism/v4.3/config/categories", 10, lambda: budget.append(True)
        )
    assert collected == rows
    assert len(calls) == len(observations) == max(1, (count + 99) // 100)
    assert secret.call_count == len(calls)


@pytest.mark.parametrize(
    "fault", ["short", "total", "missing_total", "duplicate", "wrong_type", "limit", "revoked"]
)
def test_partial_or_ambiguous_pages_never_become_complete(fault: str) -> None:
    rows = [{"extId": uid()} for _ in range(101)]
    count = 0
    budget = 0

    def before() -> None:
        nonlocal budget
        budget += 1
        if fault == "revoked" and budget == 2:
            raise CollectionFailure("permission_denied")

    def page(*args: Any) -> dict[str, Any]:
        nonlocal count
        count += 1
        document: dict[str, Any] = {
            "data": rows[:100] if count == 1 else rows[100:],
            "metadata": {"totalAvailableResults": 101},
        }
        if fault == "short":
            document["data"] = document["data"][:-1]
        if fault == "total" and count == 2:
            document["metadata"]["totalAvailableResults"] = 102
        if fault == "missing_total":
            document["metadata"] = {}
        if fault == "duplicate" and count == 2:
            document["data"] = [rows[0]]
        if fault == "wrong_type":
            document["data"] = ["invalid"]
        if fault == "limit":
            document["metadata"]["totalAvailableResults"] = 1001
        return document

    with (
        patch("inventory_worker.infrastructure.ahv_profile.exchange", side_effect=page),
        patch("inventory_worker.infrastructure.ahv_profile.secret", return_value="secret"),
        pytest.raises(CollectionFailure),
    ):
        collect_list(
            {"credential_file": "/secret"}, "/api/prism/v4.3/config/categories", 10, before
        )
    assert count <= 2
    if fault == "revoked":
        assert count == 1


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


@pytest.mark.parametrize("fault", ["cluster_config", "pc_config", "hypervisors", "hypervisor_type"])
def test_malformed_ahv_installation_objects_are_rejected(fault: str) -> None:
    stream = {
        "cluster_id": uid(),
        "prism_central_id": uid(),
        "credential_file": "/secret",
        "shared_resource_ids": [],
    }

    def read(connection: Any, path: str, headers: Any) -> dict[str, Any]:
        if "?$limit=" in path:
            return {"data": [], "metadata": {"totalAvailableResults": 0}}
        config: Any = {}
        cluster = "/clusters/" in path
        if (cluster and fault == "cluster_config") or (not cluster and fault == "pc_config"):
            config = None
        elif cluster and fault in {"hypervisors", "hypervisor_type"}:
            config = {"hypervisorTypes": None if fault == "hypervisors" else "AHV"}
        return {"data": {"extId": path.rsplit("/", 1)[-1], "config": config}}

    with (
        patch("inventory_worker.infrastructure.ahv_profile.exchange", side_effect=read),
        patch("inventory_worker.infrastructure.ahv_profile.secret", return_value="secret"),
        pytest.raises(CollectionFailure, match="invalid_response"),
    ):
        collect_ahv({"native_scope": uid()}, stream, 100, lambda: None)


@pytest.mark.parametrize("mode", ["observed", "empty", "duplicate"])
def test_ahv_policy_rule_lists_use_bounded_native_policy_rule_get(mode: str) -> None:
    project, cluster, pc, storage, subnet, policy_id, rule_id = [uid() for _ in range(7)]
    stream = {
        "kind": "target_profile", "cluster_id": cluster,
        "prism_central_id": pc, "shared_resource_ids": [],
        "credential_file": "/fixture",
    }
    approvals: list[str] = []
    native_rule = {
        "extId": rule_id, "type": "APPLICATION",
        "spec": {"srcCategoryReferences": [uid()],
                 "secretNativeDetail": "not for console"},
    }

    def exchange(connection: dict[str, Any], route: str, headers: dict[str, str]) -> dict[str, Any]:
        approvals.append(route)
        if "/clusters/" in route:
            return {"data": {"extId": cluster, "config": {
                "isAvailable": True, "hypervisorTypes": ["AHV"],
                "buildInfo": {"version": "7.6"},
                "clusterSoftwareMap": [{"softwareType": "AHV", "version": "11.2"}],
            }}}
        if "/domain-managers/" in route:
            return {"data": {"extId": pc, "config": {"buildInfo": {"version": "7.6"}}}}
        rows = []
        if "storage-containers" in route:
            rows = [{"extId": storage, "clusterExtId": cluster,
                     "isMarkedForRemoval": False, "isInternal": False}]
        elif "/subnets" in route:
            rows = [{"extId": subnet, "projectExtId": project}]
        elif f"/policies/{policy_id}/rules" in route:
            rows = [] if mode == "empty" else [native_rule]
        elif "/policies" in route:
            row: dict[str, Any] = {
                "extId": policy_id, "projectExtId": project, "state": "ENFORCE",
            }
            if mode == "duplicate":
                row["rules"] = [native_rule, native_rule]
            rows = [row]
        return {"data": rows, "metadata": {"totalAvailableResults": len(rows)}}

    with (
        patch("inventory_worker.infrastructure.ahv_profile.exchange", side_effect=exchange),
        patch("inventory_worker.infrastructure.ahv_profile.secret", return_value="fixture"),
    ):
        if mode == "duplicate":
            with pytest.raises(CollectionFailure):
                collect_ahv({"native_scope": project}, stream, 100, lambda: None)
            return
        result = collect_ahv({"native_scope": project}, stream, 100, lambda: None)
    observed = result["policies"][0]["rules"]
    assert len(approvals) == 11
    assert any(row.startswith(f"/api/microseg/v4.3/config/policies/{policy_id}/rules?") for row in approvals)
    assert result["native_qualification"] == "not_established"
    if mode == "empty":
        assert observed == []
    else:
        assert observed[0]["extId"] == rule_id
        assert observed[0]["reference_resolution"] == "unresolved"
        assert len(observed[0]["spec_sha256"]) == 64
        assert "secretNativeDetail" not in str(result)
        assert "ahv_security_rule_catalog_incomplete" not in result["holds"]
