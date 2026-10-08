"""Real pinned TLS reads, exact native subjects and individual outcome evidence."""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from test_native_http import native_tls as native_tls

from lifecycle_worker.application.native import NativeHeld, digest
from lifecycle_worker.infrastructure.evidence_probes import NativeEvidenceProbes, matches


def setup(
    tmp_path: Path, native_tls: Any
) -> tuple[NativeEvidenceProbes, str, str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    reads, peer = native_tls
    endpoint = reads.endpoints["compute"]
    tenant, caller, observer = (str(uuid4()) for _ in range(3))
    plan: dict[str, Any] = {
        "scope": {"tenant_id": tenant},
        "actor_id": str(uuid4()),
        "requester_id": str(uuid4()),
        "executor_id": str(uuid4()),
        "epoch": str(uuid4()),
        "intents": {"validate_target": digest("intent")},
    }
    binding = {
        "plan_sha256": digest(plan),
        "executor_id": plan["executor_id"],
        "epoch": plan["epoch"],
        "intent_digest": plan["intents"]["validate_target"],
        "stage": "validate_target",
        **{k: str(uuid4()) for k in ("job_id", "operation_id", "attempt_id", "grant_id")},
    }
    connection = {
        "endpoint": {
            "base_url": endpoint.base_url,
            "address": endpoint.address,
            "ca_file": str(endpoint.ca_file),
            "token_file": str(endpoint.token_file),
        },
        "header": "X-Auth-Token",
        "prefix": "",
        "reader_principal": "reader",
        "writer_principal": "writer",
        "identity_path": "/identity",
        "identity_pointer": "/id",
    }
    case = {
        "case": "service_backup",
        "connection": connection,
        "path": "/restore",
        "subject": {"pointer": "/vm_id", "operator": "equals", "value": "target-vm"},
        "predicates": [
            {"pointer": "/status", "operator": "equals", "value": "completed"},
            {"pointer": "/checksum", "operator": "equals", "value": digest("dataset")},
            {"pointer": "/observed_at", "operator": "maximum_age_seconds", "value": 10},
        ],
        "requirement_sha256": digest("approved-backup-configuration"),
        "policy_results": {},
    }
    manifest = {
        "plan_sha256": digest(plan),
        "caller_id": caller,
        "stage": "validate_target",
        "phase": "after",
        "expires_at": 200,
        "cases": [case],
    }
    registry = tmp_path / "probes.json"
    registry.write_text(json.dumps({"schema_version": 1, "assignments": [manifest]}))
    from urllib.parse import urlsplit

    base = urlsplit(endpoint.base_url).path
    peer["routes"] = {
        base + "/identity": {"status": 200, "body": b'{"id":"reader"}'},
        base + "/restore": {
            "status": 200,
            "body": json.dumps(
                {
                    "vm_id": "target-vm",
                    "status": "completed",
                    "checksum": digest("dataset"),
                    "observed_at": 99,
                }
            ).encode(),
        },
    }
    return (
        NativeEvidenceProbes(registry, observer, lambda: 100),
        tenant,
        caller,
        {"plan": plan, "binding": binding, "phase": "after"},
        peer,
        manifest,
    )


def test_observer_reads_native_principal_and_restore_checksum(
    native_tls: Any, tmp_path: Path
) -> None:
    probe, tenant, caller, body, peer, manifest = setup(tmp_path, native_tls)
    result = probe.observe(tenant, caller, body)
    record = result["records"][0]
    assert record["case"] == "service_backup" and record["binding_sha256"] == digest(
        body["binding"]
    )
    assert record["requirement_sha256"] == manifest["cases"][0]["requirement_sha256"]
    assert record["outcome"] == "passed" and len(record["evidence_sha256"]) == 64
    assert all(r["method"] == "GET" for r in peer["requests"])
    assert len(peer["requests"]) == 2
    assert "checksum" not in record and "connection" not in record


@pytest.mark.parametrize(
    "fault", ["tenant", "caller", "scope", "subject", "failed", "stale", "principal", "revoked"]
)
def test_no_passed_evidence_for_foreign_partial_stale_or_revoked_native_reads(
    native_tls: Any, tmp_path: Path, fault: str
) -> None:
    probe, tenant, caller, body, peer, _ = setup(tmp_path, native_tls)
    if fault == "tenant":
        tenant = str(uuid4())
    if fault == "caller":
        caller = str(uuid4())
    if fault == "scope":
        body["binding"]["intent_digest"] = digest("other")
    route = next(v for k, v in peer["routes"].items() if k.endswith("/restore"))
    payload = json.loads(route["body"])
    if fault == "subject":
        payload["vm_id"] = "source-vm"
    if fault == "failed":
        payload["status"] = "queued"
    if fault == "stale":
        payload["observed_at"] = 80
    route["body"] = json.dumps(payload).encode()
    if fault == "principal":
        next(v for k, v in peer["routes"].items() if k.endswith("/identity"))["body"] = (
            b'{"id":"writer"}'
        )
    if fault == "revoked":
        next(v for k, v in peer["routes"].items() if k.endswith("/identity"))["before_response"] = (
            lambda: probe.registry.write_text("{}")
        )
    with pytest.raises(NativeHeld):
        probe.observe(tenant, caller, body)


def test_predicates_reject_type_substitution_and_future_or_missing_data() -> None:
    assert not matches(
        {"value": 1}, {"pointer": "/value", "operator": "equals", "value": True}, 100
    )
    assert not matches(
        {"value": 101}, {"pointer": "/value", "operator": "maximum_age_seconds", "value": 10}, 100
    )
    with pytest.raises(NativeHeld):
        matches({}, {"pointer": "/value", "operator": "equals", "value": "anything"}, 100)


@pytest.mark.parametrize(
    "case", ["service_backup", "guest_boot", "security_rule_web", "dataset_root"]
)
def test_configured_or_stale_measurement_cannot_be_restamped_as_new_acceptance(
    native_tls: Any, tmp_path: Path, case: str
) -> None:
    probe, tenant, caller, body, peer, manifest = setup(tmp_path, native_tls)
    selected = manifest["cases"][0]
    selected["case"] = case
    selected["predicates"] = [selected["predicates"][0]]
    probe.registry.write_text(json.dumps({"schema_version": 1, "assignments": [manifest]}))
    with pytest.raises(NativeHeld, match="freshness_required"):
        probe.observe(tenant, caller, body)
    assert not peer["requests"]


@pytest.mark.parametrize("per_path", [True, False])
def test_policy_requires_fresh_individual_allow_and_deny_measurements(
    native_tls: Any, tmp_path: Path, per_path: bool
) -> None:
    probe, tenant, caller, body, peer, manifest = setup(tmp_path, native_tls)
    selected = manifest["cases"][0]
    selected["case"] = "policy_paths"
    selected["policy_results"] = {"web": "allow", "admin": "deny"}
    selected["predicates"] = [
        {"pointer": "/observed_at", "operator": "maximum_age_seconds", "value": 10}
    ]
    measured: dict[str, Any] = {"vm_id": "target-vm", "observed_at": 99}
    for key, outcome in selected["policy_results"].items():
        measured[key] = {"result": {"id": key, "outcome": outcome}, "observed_at": 99}
        selected["predicates"].append(
            {
                "pointer": "/" + key + "/result",
                "operator": "equals",
                "value": {"id": key, "outcome": outcome},
            }
        )
        if per_path:
            selected["predicates"].append(
                {
                    "pointer": "/" + key + "/observed_at",
                    "operator": "maximum_age_seconds",
                    "value": 10,
                }
            )
    next(v for k, v in peer["routes"].items() if k.endswith("/restore"))["body"] = json.dumps(
        measured
    ).encode()
    probe.registry.write_text(json.dumps({"schema_version": 1, "assignments": [manifest]}))
    if per_path:
        assert (
            probe.observe(tenant, caller, body)["records"][0]["policy_results"]
            == selected["policy_results"]
        )
    else:
        with pytest.raises(NativeHeld, match="policy_measurement_required"):
            probe.observe(tenant, caller, body)
