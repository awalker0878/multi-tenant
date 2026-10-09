"""Native composition re-reads owners and cannot turn simulation consent into writes."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from test_migration import MigrationOwners, migration_input, migration_plan
from test_native_effects import peer  # noqa: F401
from test_native_workflow import Owners as ProvisionOwners
from test_native_workflow import plan as provision_plan

from lifecycle.bootstrap.native_server import NativeControl, configuration
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.infrastructure.native_owners import (
    NativeOwnerConfiguration,
    NativeOwners,
    NativeOwnerTransport,
)


def fixture(tmp_path: Path) -> tuple[NativeOwners, dict[str, Any], dict[str, Any], dict[str, Any]]:
    p = migration_plan()
    scope = p["scope"]
    assignment = {
        k: p[k]
        for k in (
            "plan_id",
            "plan_revision",
            "plan_digest",
            "approval_id",
            "actor_id",
            "executor_id",
            "campaign_id",
            "epoch",
        )
    }
    assignment["tenant_id"] = scope["tenant_id"]
    native = {
        "schema_version": 1,
        "scope": scope,
        "migration": p["migration"],
        "intents": p["intents"],
        "native": {
            k: p[k]
            for k in (
                "configuration",
                "tuple_digest",
                "source_revision",
                "ownership_digest",
                "custody_id",
                "custody_generation",
                "policy_cases",
            )
        },
        "source_job_id": None,
        "recipe_sha256": digest("recipe"),
        "recipe_id": str(uuid4()),
        "base_plan_id": str(uuid4()),
    }
    native["native"]["ownership_digest"] = digest([])
    content = {
        "action": "application.migrate",
        "execution_ready": True,
        "lane": "operational",
        "holds": [],
        "scope": scope | {"native_scope": "project:" + scope["project_id"]},
        "ownership": [],
        "native_api": {k: p[k] for k in ("custody_id", "custody_generation")},
        "valid_until": 1800,
        "input_fresh_until": 1800,
        "native_migration": native,
        "migration_campaign": {
            "route_sha256": digest("route"),
            "sizes": {},
            "demands": {},
            "mode": "cutover",
            "method": "VM_COLD_EXPORT",
        },
    }
    binding = {
        "plan_id": p["plan_id"],
        "revision": 1,
        **{k: scope[k] for k in ("tenant_id", "site_id", "environment", "resource_id")},
        "requested_by": p["requester_id"],
        "executor_ids": [p["actor_id"]],
        "lane": "operational",
        "canonicalization": "p05-json-v1",
        "valid_until": 1800,
        "content_digest": digest(content),
    }
    binding["digest"] = digest(binding)
    assignment["plan_digest"] = binding["digest"]
    # Synthetic E2 fixture only: production reads this from Planning after
    # current Catalogue, Inventory and independent Assurance checks.
    receipt = {
        "schema_version": 2, "kind": "migration_workload_readiness",
        "scope": {
            "tenant_id": scope["tenant_id"],
            "application_id": scope["resource_id"],
            "environment_id": scope["environment"],
            "site_id": scope["site_id"],
        },
        "route_sha256": content["migration_campaign"]["route_sha256"],
        "tranche_sha256": digest("tranche"), "release_sha256": digest("release"),
        "source": {
            "platform": "vmware", "installation_id": "source-installation",
            "profile_sha256": p["migration"]["source"]["profile_sha256"],
            "versions": {"api": "8.0"},
        },
        "target": {
            "platform": "openstack", "installation_id": "target-installation",
            "profile_sha256": p["migration"]["target"]["profile_sha256"],
            "versions": {"api": "2.1"},
        },
        "method": "cold_export",
        "api_compatibility": {
            "status": "eligible", "operationally_eligible": True,
            "administrator_alerts": [], "native_write_authorized": False,
            "cases": [{
                "capability_id": "vm.disk.transfer", "side": "source",
                "criticality": "critical", "status": "eligible",
                "reason": "synthetic independent evidence",
                "evidence_sha256": digest("api-qualified"),
                "selected_api_family": "vim", "selected_api_version": "8.0",
                "omission_accepted": False, "expires_at": 1800,
            }],
        },
        "native_e3_qualified": True, "receiving_e4_accepted": True,
        "status": "eligible", "holds": [], "evaluated_at": 1000,
        "expires_at": 1800, "workload_admission_authorized": False,
        "native_write_authorized": False,
    }
    source_generation = str(uuid4())
    source_tuple = p["migration"]["source"]["tuple_sha256"]
    target_tuple = p["migration"]["target"]["tuple_sha256"]
    reconciliation = {
        "schema_version": 1, "catalogue_revision_id": str(uuid4()),
        "catalogue_sha256": digest("intent"),
        "source_identity_sha256": digest("native-identity"),
        "source_generation_id": source_generation,
        "source_profile_sha256": p["migration"]["source"]["profile_sha256"],
        "source_observation_sha256": digest("source-observation"),
        "native_review_sha256": p["migration"]["review"]["digest"],
        "status": "matched", "holds": [], "workloads": [{
            "workload_id": str(uuid4()), "status": "matched", "holds": [],
            "source_identity_sha256": digest("native-identity"),
            "field_dispositions": [{
                "field": "cpu.count", "disposition": "matched", "required": True,
                "desired_value": "2", "observed_value": "2",
                "evidence_source": "inventory_native_profile",
                "evidence_age_seconds": 1, "next_action": "none",
            }],
        }], "expires_at": 1800, "native_write_authorized": False,
    }
    reconciliation["reconciliation_sha256"] = digest(reconciliation)
    coverages = []
    for side, installation, tuple_sha, generation in (
        ("source", "source-installation", source_tuple, source_generation),
        ("target", "target-installation", target_tuple, str(uuid4())),
        ("owner", "source-installation", source_tuple, source_generation),
    ):
        coverage = {
            "schema_version": 1,
            "platform": "openstack" if side == "target" else "vmware", "scope": side,
            "installation_id": installation, "generation_id": generation,
            "installed_tuple_sha256": tuple_sha,
            "manifest_sha256": digest("field-manifest"),
            "evaluated_at": 1000, "expires_at": 1800,
            "status": "complete", "holds": [],
            "attributes": [{"attribute_id": "identity", "status": "observed",
                            "reason": "native", "severity": "critical"}],
            "independent_e3_e4_qualification": False,
            "native_write_authorized": False,
        }
        coverage["coverage_sha256"] = digest(coverage)
        coverages.append(coverage)
    receipt["workload_reconciliation"] = reconciliation
    receipt["collection_coverages"] = coverages
    receipt["readiness_sha256"] = digest(receipt)
    record = {
        "binding": binding, "content": content, "invalidated": False,
        "migration_readiness": receipt,
    }
    approval = {
        "allowed": True,
        "tenant_id": scope["tenant_id"],
        "actor_id": p["actor_id"],
        "approval_id": p["approval_id"],
        "plan_digest": binding["digest"],
        "authority_use": "native_approval",
        "native_write_authorized": False,
        "requester_id": p["requester_id"],
        "executor_fingerprint": digest("executor"),
        "evaluated_at": 1000,
        "approval": {
            "state": "approved",
            "revoked": False,
            "approver_grant_current": True,
            "approver_id": p["approver_id"],
            "plan_id": p["plan_id"],
            "plan_revision": 1,
            "plan_digest": binding["digest"],
            "expires_at": 1800,
            "scope": {k: scope[k] for k in ("site_id", "environment", "resource_id")},
        },
    }
    peers = {}
    for index, name in enumerate(
        ("planning", "governance", "inventory", "custody", "observer", "worker", "caller")
    ):
        token = tmp_path / (name + ".token")
        token.write_text(chr(97 + index) * 64)
        ca = tmp_path / (name + ".pem")
        ca.write_text("synthetic certificate, no outbound calls in this fixture")
        peers[name] = {
            "origin": "https://" + name + ".invalid",
            "address": "127.0.0.1",
            "ca_file": str(ca),
            "credential_file": str(token),
        }
    config = {
        "schema_version": 1,
        "expires_at": 2000,
        "owners": {k: v for k, v in peers.items() if k not in {"worker", "caller"}},
        "assignments": [assignment],
        "workers": [
            {
                "tenant_id": scope["tenant_id"],
                "executor_id": p["executor_id"],
                "endpoint": peers["worker"],
                "caller_file": peers["caller"]["credential_file"],
            }
        ],
    }
    path = tmp_path / "owners.json"
    path.write_text(json.dumps(config))
    config_source = NativeOwnerConfiguration(path, lambda: 1000)
    transport = MagicMock(spec=NativeOwnerTransport)
    state: dict[str, Any] = {
        "record": record,
        "approval": approval,
        "config": config,
        "path": path,
        "plan": None,
        "fault": None,
    }

    def request(owner: str, method: str, route: str, body: Any = None) -> dict[str, Any]:
        if owner == "planning":
            return deepcopy(state["record"])
        if owner == "governance":
            return deepcopy(state["approval"])
        if owner == "inventory":
            data = migration_input(state["plan"])
            if state["fault"] == "inventory":
                data["current"] = False
            return data
        if route == "/v1/native-custody/epoch":
            return {"epoch": state["plan"]["epoch"], "evaluated_at": 1000, "expires_at": 1100}
        if owner == "custody":
            value = MigrationOwners(state["plan"]).current(state["plan"], body["binding"])
            if state["fault"] == "custody":
                value["provider_fence_current"] = False
            return value
        if owner == "observer":
            return {
                "records": MigrationOwners(state["plan"]).observe(
                    state["plan"], body["binding"], body["phase"]
                )
            }
        raise AssertionError(owner)

    transport.request.side_effect = request
    owners = NativeOwners(config_source, transport, lambda: 1000)
    state["plan"] = owners.resolve(scope["tenant_id"], assignment)
    return owners, assignment, state, config


def test_complete_proposal_resolves_then_checks_every_current_owner(tmp_path: Path) -> None:
    owners, ref, state, _ = fixture(tmp_path)
    p = state["plan"]
    assert p["plan_digest"] == ref["plan_digest"]
    assert p["expires_at"] == 1800
    admission = {"job_id": str(uuid4()), "stage": "admission", "plan_sha256": digest(p)}
    assert owners.current(p, admission)["native_write_authorized"] is True
    for fault in ("inventory", "custody"):
        state["fault"] = fault
        with pytest.raises(Rejected):
            owners.current(p, admission)


@pytest.mark.parametrize("purpose", ["provision", "retire"])
def test_native_proposal_resolves_without_migration_assumptions(
    tmp_path: Path, purpose: str
) -> None:
    owners, ref, state, config = fixture(tmp_path)
    record = state["record"]
    content = record["content"]
    native = content.pop("native_migration")
    del native["migration"]
    native["purpose"] = purpose
    native["intents"] = (
        provision_plan()["intents"]
        if purpose == "provision"
        else {s: digest(s) for s in ("retire", "release")}
    )
    native["source_job_id"] = str(uuid4()) if purpose == "retire" else None
    content["native_provisioning"] = native
    content["action"] = "application." + purpose
    del content["migration_campaign"]
    binding = record["binding"]
    binding["content_digest"] = digest(content)
    binding["digest"] = digest({k: v for k, v in binding.items() if k != "digest"})
    ref["plan_digest"] = binding["digest"]
    config["assignments"][0]["plan_digest"] = binding["digest"]
    state["path"].write_text(json.dumps(config))
    state["approval"]["plan_digest"] = binding["digest"]
    state["approval"]["approval"]["plan_digest"] = binding["digest"]
    state["plan"] = p = owners.resolve(ref["tenant_id"], ref)
    assert p["purpose"] == purpose and "migration" not in p
    transport: Any = owners.transport
    original = transport.request.side_effect
    custody = ProvisionOwners(p)

    def request(owner: str, method: str, route: str, body: Any = None) -> dict[str, Any]:
        if route == "/v1/native-custody/checks":
            return custody.current(p, body["binding"])
        return dict(original(owner, method, route, body))

    transport.request.side_effect = request
    admission = {"job_id": str(uuid4()), "stage": "admission", "plan_sha256": digest(p)}
    assert owners.current(p, admission)["native_write_authorized"] is True
    custody.authority_changes["configuration_current"] = False
    with pytest.raises(Rejected, match="native_authority_not_current"):
        owners.current(p, admission)


@pytest.mark.parametrize(
    "fault",
    [
        "simulation",
        "expiry",
        "approver",
        "requester",
        "scope",
        "revoked",
        "plan",
        "worker",
        "assignment",
    ],
)
def test_changed_native_approval_assignment_or_proposal_never_resolves(
    tmp_path: Path, fault: str
) -> None:
    owners, ref, state, config = fixture(tmp_path)
    if fault == "simulation":
        state["approval"]["authority_use"] = "simulation_boundary"
    elif fault == "expiry":
        state["approval"]["approval"]["expires_at"] = 1000
    elif fault == "approver":
        state["approval"]["approval"]["approver_id"] = ref["actor_id"]
    elif fault == "requester":
        state["approval"]["requester_id"] = str(uuid4())
    elif fault == "scope":
        state["approval"]["approval"]["scope"]["site_id"] = str(uuid4())
    elif fault == "revoked":
        state["approval"]["approval"]["revoked"] = True
    elif fault == "plan":
        state["record"]["content"]["native_migration"]["migration"]["method"] = (
            "EXTERNAL_BLOCK_REPLICATION"
        )
    elif fault == "worker":
        config["workers"][0]["tenant_id"] = str(uuid4())
        state["path"].write_text(json.dumps(config))
    else:
        config["assignments"] = []
        state["path"].write_text(json.dumps(config))
    with pytest.raises(Rejected):
        owners.resolve(ref["tenant_id"], ref)


def test_caller_rotation_duplicates_and_foreign_plan_are_denied(tmp_path: Path) -> None:
    owners, ref, state, config = fixture(tmp_path)
    auth = owners.configuration
    assert auth.authorize_worker("g" * 64) == (ref["tenant_id"], ref["executor_id"])
    with pytest.raises(Rejected):
        auth.assignment(str(uuid4()), ref)
    Path(config["workers"][0]["caller_file"]).write_text("z" * 64)
    with pytest.raises(Rejected):
        auth.authorize_worker("g" * 64)
    assert auth.authorize_worker("z" * 64)
    config["owners"]["observer"]["credential_file"] = config["owners"]["custody"]["credential_file"]
    state["path"].write_text(json.dumps(config))
    with pytest.raises(Rejected):
        auth.load()


def test_changed_plan_after_admission_holds_boundary(tmp_path: Path) -> None:
    owners, ref, state, _ = fixture(tmp_path)
    state["record"]["invalidated"] = True
    with pytest.raises(Rejected):
        owners.current(state["plan"], {"stage": "capture"})


def test_owner_tls_reads_are_pinned_bounded_and_never_retried(peer: Any, tmp_path: Path) -> None:  # noqa: F811
    native, wire = peer
    owners, _, _, _ = fixture(tmp_path)
    source = MagicMock(spec=NativeOwnerConfiguration)
    spec = {
        "origin": native.origin,
        "address": native.address,
        "ca_file": str(native.ca_file),
        "credential_file": str(native.credential_file),
    }
    source.load.return_value = {"owners": {"custody": spec}}
    transport = NativeOwnerTransport(source)
    wire["body"] = b'{"epoch":"fixture"}'
    assert transport.request("custody", "POST", "/v1/native-custody/checks", {}) == {
        "epoch": "fixture"
    }
    wire["body"] = b'{"allowed":true,"allowed":false}'
    with pytest.raises(Rejected):
        transport.request("custody", "POST", "/v1/native-custody/checks", {})
    assert len(wire["requests"]) == 2


def test_bootstrap_does_not_expose_simulation_and_uses_native_binding_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owners, _, state, config = fixture(tmp_path)
    service = tmp_path / "service.json"
    ca = config["owners"]["planning"]["ca_file"]
    service.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "owners_file": str(state["path"]),
                "tls_cert_file": ca,
                "tls_key_file": ca,
            }
        )
    )
    monkeypatch.setattr(
        "lifecycle.bootstrap.native_server.NativeWorkerEffects", mock := MagicMock()
    )
    monkeypatch.setattr("lifecycle.bootstrap.native_server.time.time", lambda: 1000)
    control = NativeControl(service)
    p = state["plan"]
    grant = {
        "executor_id": p["executor_id"],
        "native_binding": {"tenant_id": p["scope"]["tenant_id"]},
    }
    control.execute(grant)
    mock.return_value.execute.assert_called_once_with(grant)
    grant["native_binding"]["tenant_id"] = str(uuid4())
    with pytest.raises(Rejected):
        control.execute(grant)
    assert configuration(service)["schema_version"] == 1
