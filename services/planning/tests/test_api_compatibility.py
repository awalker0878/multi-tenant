"""Migration API compatibility: mixed-version admission, optional-impact warnings and denial."""

from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest
from test_expansion import baseline, route_for

from planning.application.migration_support import MigrationSupport
from planning.domain.api_compatibility import evaluate, usage
from planning.domain.model import Actor, Rejected, digest


def selected() -> dict[str, Any]:
    route = route_for("vmware", "openstack")
    route["api_usage"] = [
        {
            "capability_id": "vm.disk.export",
            "side": "source",
            "criticality": "critical",
            "reason": "All authoritative disk bytes must be exported.",
        },
        {
            "capability_id": "vm.disk.import",
            "side": "target",
            "criticality": "critical",
            "reason": "All disks must be imported into the destination.",
        },
        {
            "capability_id": "network.firewall.cosmetic_rule",
            "side": "target",
            "criticality": "optional",
            "reason": "A redundant non-security cosmetic rule cannot be recreated.",
        },
    ]
    return route


def owner_input(route: dict[str, Any], now: int = 100) -> dict[str, Any]:
    source = route["source"]
    target = route["target"]
    return {
        "route_sha256": digest(route),
        "environments": {
            "source": {
                "installation_id": source["installation_id"],
                "profile_sha256": source["profile_sha256"],
                "observed_at": now - 10,
                "expires_at": now + 40,
                "source": "live_probe",
                "evidence_sha256": "5" * 64,
                "apis": {"vmware.vi_json": ["8.0.3.0", "9.0.0.0"]},
                "entitlements": {"vm.disk.export": "allowed"},
            },
            "target": {
                "installation_id": target["installation_id"],
                "profile_sha256": target["profile_sha256"],
                "observed_at": now - 10,
                "expires_at": now + 40,
                "source": "live_probe",
                "evidence_sha256": "6" * 64,
                "apis": {"openstack.nova": ["2.1", "2.104"]},
                "entitlements": {
                    "vm.disk.import": "allowed",
                    "network.firewall.cosmetic_rule": "unknown",
                },
            },
        },
        "observations": [
            {
                "installation_id": source["installation_id"],
                "profile_sha256": source["profile_sha256"],
                "capability_id": "vm.disk.export",
                "api_family": "vmware.vi_json",
                "api_version": "8.0.3.0",
                "result": "supported",
                "source": "live_probe",
                "observed_at": now - 10,
                "expires_at": now + 40,
                "evidence_sha256": "a" * 64,
                "qualification_level": "E3",
                "qualification_decision": "accepted",
                "qualification_sha256": "c" * 64,
            },
            {
                "installation_id": target["installation_id"],
                "profile_sha256": target["profile_sha256"],
                "capability_id": "vm.disk.import",
                "api_family": "openstack.nova",
                "api_version": "2.104",
                "result": "supported",
                "source": "live_probe",
                "observed_at": now - 10,
                "expires_at": now + 40,
                "evidence_sha256": "b" * 64,
                "qualification_level": "E3",
                "qualification_decision": "accepted",
                "qualification_sha256": "d" * 64,
            },
        ],
        "omissions": [],
    }


def test_different_api_releases_do_not_block_qualified_operations() -> None:
    row = selected()
    result = evaluate(row, owner_input(row), 100)
    assert result["status"] == "conditional"
    assert [case["status"] for case in result["cases"]] == [
        "eligible", "eligible", "unknown",
    ]
    assert result["administrator_alerts"] == [
        {
            "capability_id": "network.firewall.cosmetic_rule",
            "side": "target",
            "severity": "warning",
            "reason": "api_entitlement_unconfirmed",
            "impact": "A redundant non-security cosmetic rule cannot be recreated.",
            "action": "approve_and_omit_nonessential_feature",
            "omission_accepted": False,
        }
    ]


def test_multiple_negotiated_versions_select_only_a_qualified_compatible_release() -> None:
    row = selected()
    evidence = owner_input(row)
    older = deepcopy(evidence["observations"][1])
    older.update(
        api_version="2.1",
        result="unsupported",
        evidence_sha256="7" * 64,
        qualification_sha256=None,
        qualification_level="none",
        qualification_decision="not_reviewed",
    )
    evidence["observations"].append(older)
    assessment = evaluate(row, evidence, 100)
    assert assessment["cases"][1]["status"] == "eligible"
    assert assessment["cases"][1]["selected_api_family"] == "openstack.nova"
    assert assessment["cases"][1]["selected_api_version"] == "2.104"
    # If the qualifying release disappears, the remaining older release
    # cannot inherit its proof, even though it is on the same installation.
    evidence["environments"]["target"]["apis"]["openstack.nova"] = ["2.1"]
    assert evaluate(row, evidence, 100)["status"] == "blocked"


def test_missing_or_unqualified_disk_prevents_approval() -> None:
    row = selected()
    evidence = owner_input(row)
    for reason in ("removed", "expired", "spec", "version", "entitlement"):
        bad = deepcopy(evidence)
        if reason == "removed":
            bad["observations"].pop(1)
        elif reason == "expired":
            bad["observations"][1]["expires_at"] = 100
        elif reason == "spec":
            bad["observations"][1]["source"] = "spec_diff"
        elif reason == "version":
            bad["environments"]["target"]["apis"]["openstack.nova"] = ["2.1"]
        else:
            bad["environments"]["target"]["entitlements"]["vm.disk.import"] = "denied"
        result = evaluate(row, bad, 100)
        assert result["status"] == "blocked"
        assert result["operationally_eligible"] is False
        assert result["administrator_alerts"][0]["severity"] == "blocker"


def test_stale_destination_version_inventory_never_inherits_old_support() -> None:
    row = selected()
    evidence = owner_input(row)
    evidence["environments"]["target"]["expires_at"] = 100
    result = evaluate(row, evidence, 100)
    assert result["status"] == "blocked"
    assert result["cases"][1]["reason"] == "api_environment_discovery_stale"


def test_optional_omission_needs_exact_scope_E4_owner_acceptance() -> None:
    row = selected()
    evidence = owner_input(row)
    tenant, application, environment = (str(uuid4()) for _ in range(3))
    ack: dict[str, Any] = {
        "capability_id": "network.firewall.cosmetic_rule",
        "side": "target",
        "route_sha256": digest(row),
        "tenant_id": tenant,
        "application_id": application,
        "environment_id": environment,
        "decision": "accepted",
        "evidence_level": "E4",
        "expires_at": 150,
        "approval_sha256": "e" * 64,
        "effect_suppressed_sha256": "1" * 64,
    }
    evidence["omissions"] = [ack]
    result = evaluate(
        row, evidence, 100, tenant_id=tenant,
        application_id=application, environment_id=environment,
    )
    assert result["status"] == "eligible"
    assert result["operationally_eligible"] is True
    assert result["administrator_alerts"][0]["omission_accepted"] is True
    for changed in (
        {"decision": "not_reviewed"},
        {"evidence_level": "E2"},
        {"expires_at": 100},
        {"application_id": str(uuid4())},
        {"route_sha256": "f" * 64},
        {"effect_suppressed_sha256": None},
    ):
        untrusted = deepcopy(evidence)
        untrusted["omissions"] = [ack | changed]
        assert (
            evaluate(
                row, untrusted, 100, tenant_id=tenant,
                application_id=application, environment_id=environment,
            )["status"] == "conditional"
        )


def test_safety_requirements_cannot_be_declared_optional() -> None:
    for capability in (
        "vm.disk.snapshot", "vm.boot.verify", "storage.data.encrypt",
        "security.isolation.project", "network.required.application_flow",
    ):
        with pytest.raises(Rejected, match="safety_cannot_be_optional"):
            usage([{
                "capability_id": capability,
                "side": "target",
                "criticality": "optional",
                "reason": "Attempted omission.",
            }])


def test_forged_or_ambiguous_installation_evidence_fails_closed() -> None:
    row = selected()
    evidence = owner_input(row)
    evidence["environments"]["target"]["installation_id"] = str(uuid4())
    with pytest.raises(Rejected, match="scope_changed"):
        evaluate(row, evidence, 100)
    evidence = owner_input(row)
    evidence["observations"].append(deepcopy(evidence["observations"][1]))
    assert evaluate(row, evidence, 100)["status"] == "blocked"


def test_migration_support_preview_and_execution_recheck_use_same_gate() -> None:
    selected_tranche = baseline()
    for i, route in enumerate(selected_tranche["routes"]):
        route["source"]["profile_sha256"] = digest([i, "source"])
        route["target"]["profile_sha256"] = digest([i, "target"])
    route = next(
        row for row in selected_tranche["routes"]
        if row["source"]["platform"] == "vmware" and row["target"]["platform"] == "openstack"
    )
    route["api_usage"] = selected()["api_usage"]
    owner = owner_input(route)
    actor = Actor(str(uuid4()), str(uuid4()), "plan.read", str(uuid4()), str(uuid4()))
    site = str(uuid4())
    qualification = {
        "route_sha256": digest(route),
        "tranche_sha256": digest(selected_tranche),
        "release_sha256": selected_tranche["release_sha256"],
        "level": "E3",
        "decision": "accepted",
        "revoked": False,
        "expires_at": 180,
        "evidence_sha256": "f" * 64,
    }
    support = MigrationSupport(
        lambda *_: selected_tranche,
        lambda *_: [qualification],
        lambda: 100,
        lambda *_: owner,
    )
    preview = next(
        direction for direction in support.read(actor, site)["directions"]
        if direction["direction"] == "vmware->openstack"
    )["routes"][0]
    assert preview["api_compatibility"]["status"] == "conditional"
    assert "api_capabilities_unresolved" in preview["blockers"]
    binding = {
        "source": {"profile_sha256": route["source"]["profile_sha256"]},
        "target": {"profile_sha256": route["target"]["profile_sha256"]},
        "method": "VM_COLD_EXPORT",
    }
    with pytest.raises(Rejected, match="api_capabilities_unresolved"):
        support.require(actor, site, binding)
    owner["omissions"] = [{
        "capability_id": "network.firewall.cosmetic_rule",
        "side": "target",
        "route_sha256": digest(route),
        "tenant_id": actor.tenant,
        "application_id": actor.application,
        "environment_id": actor.environment,
        "decision": "accepted",
        "evidence_level": "E4",
        "expires_at": 150,
        "approval_sha256": "e" * 64,
        "effect_suppressed_sha256": "1" * 64,
    }]
    upgraded = next(
        direction for direction in support.read(actor, site)["directions"]
        if direction["direction"] == "vmware->openstack"
    )["routes"][0]
    assert upgraded["api_compatibility"]["status"] == "eligible"
    support.require(actor, site, binding)
