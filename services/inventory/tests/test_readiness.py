"""Task applicability and authenticated evidence never grant native authority."""

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from test_discovery import Campaign

from inventory.application.discovery import uid
from inventory.application.operator_inputs import OperatorInputs
from inventory.domain.discovery import Rejected, canonical, digest
from inventory.domain.readiness import check_fields, requirements, validate_context
from inventory.infrastructure.readiness_evidence import read_evidence
from inventory.infrastructure.readiness_publication import publish

pytest_plugins = ["test_discovery"]


def required(operation: str, method: str | None = None, target: str = "openstack") -> set[str]:
    return {
        f["id"]
        for f in requirements({"operation": operation, "method": method}, "vmware", target)
        if f["required"]
    }


def test_requirements_follow_operation_method_and_observed_platform() -> None:
    cold = required("migrate", "VM_COLD_EXPORT")
    assert "source_writer_ref" in cold and "image_writer_ref" in cold
    assert "delta_ref" not in cold
    assert "delta_ref" in required("migrate", "VM_SNAPSHOT_BASELINE_APP_DELTA")
    assert "image_writer_ref" not in required("migrate", "VM_COLD_EXPORT", "ahv")
    assert "source_writer_ref" not in required("provision")
    assert "guest_recipe_ref" not in required("retire")
    assert "receiving_team_ref" in required("operate")
    assert required("discover") == {
        "source_observer_ref",
        "target_observer_ref",
        "account_scope_ref",
        "trust_bundle_ref",
    }
    for field in requirements(None, None, None):
        assert not field["required"] and field["example"] and field["format"] and field["owner"]


@pytest.mark.parametrize(
    "context",
    [
        {"operation": "unsupported", "method": None},
        {"operation": "discover", "method": "VM_COLD_EXPORT"},
        {"operation": "migrate", "method": None},
        {"operation": "migrate", "method": "VM_COLD_EXPORT", "native_write_authorized": True},
    ],
)
def test_context_cannot_weaken_native_admission(context: dict[str, Any]) -> None:
    with pytest.raises(Rejected):
        validate_context(context)


def test_evidence_states_do_not_confuse_supplied_with_verified() -> None:
    fields = requirements({"operation": "migrate", "method": "VM_COLD_EXPORT"}, "vmware", "ahv")
    values = {"max_outage_seconds": 0, "source_writer_ref": "secret:source"}
    checks = {c["field_id"]: c for c in check_fields(fields, values, {}, False)}
    assert checks["max_outage_seconds"]["state"] == "unverified"
    assert checks["target_writer_ref"]["state"] == "missing"
    assert checks["image_writer_ref"]["state"] == "not_applicable"
    checks = {
        c["field_id"]: c
        for c in check_fields(fields, values, {"source_writer_ref": {"state": "verified"}}, True)
    }
    assert checks["source_writer_ref"]["state"] == "stale"


@pytest.fixture
def evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    private = Ed25519PrivateKey.generate()
    original = tmp_path / "observation.json"
    original.write_bytes(b'{"fixture":"synthetic owner observation"}')
    original.chmod(0o600)
    payload = {
        "schema_version": 1,
        "producer_id": "platform-observer",
        "tenant_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "site_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "packet_digest": "a" * 64,
        "configuration_digest": "b" * 64,
        "checks": [
            {
                "field_id": "source_writer_ref",
                "value_sha256": digest("secret:source"),
                "result": "verified",
                "observed_at": 100,
                "expires_at": 200,
                "evidence_file": str(original),
                "evidence_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
            }
        ],
    }
    receipt = tmp_path / "receipt.json"

    def sign() -> None:
        receipt.write_text(
            json.dumps(
                {
                    "payload": payload,
                    "signature": base64.b64encode(
                        private.sign(
                            b"multi-tenant/commissioning-receipt/v1\x00"
                            + canonical(payload).encode()
                        )
                    ).decode(),
                }
            )
        )
        receipt.chmod(0o600)

    sign()
    registry = tmp_path / "registry.json"
    config = {
        "schema_version": 1,
        "producers": [
            {
                "id": "platform-observer",
                "public_key": base64.b64encode(private.public_key().public_bytes_raw()).decode(),
                "expires_at": 300,
                "fields": ["source_writer_ref"],
                "scopes": [{"tenant_id": payload["tenant_id"], "site_id": payload["site_id"]}],
                "receipts": [str(receipt)],
            }
        ],
    }
    registry.write_text(json.dumps(config))
    registry.chmod(0o600)
    monkeypatch.setenv("INVENTORY_COMMISSIONING_EVIDENCE_FILE", str(registry))
    return payload, sign, receipt, original, registry, config


def read(
    now: int = 150, tenant: str = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", packet: str = "a" * 64
) -> dict[str, Any]:
    return read_evidence(
        tenant,
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        packet,
        "b" * 64,
        {"source_writer_ref": "secret:source"},
        now,
    )


def test_receipts_require_exact_packet_original_bytes_and_current_producer(evidence: Any) -> None:
    payload, sign, receipt, original, registry, config = evidence
    assert read()["source_writer_ref"]["state"] == "verified"
    assert read(200)["source_writer_ref"]["state"] == "stale"
    assert read(99)["source_writer_ref"]["state"] == "stale"
    assert read(tenant="cccccccc-cccc-4ccc-8ccc-cccccccccccc") == {}
    assert read(packet="c" * 64) == {}
    payload["checks"][0]["result"] = "failed"
    sign()
    assert read()["source_writer_ref"]["state"] == "failed"
    original.write_bytes(b"changed")
    assert read()["source_writer_ref"]["state"] == "unavailable"
    assert str(original) not in str(read())
    config["producers"] = []
    registry.write_text(json.dumps(config))
    assert read() == {}


@pytest.mark.parametrize(
    "fault", ["signature", "field", "value", "duplicate", "symlink", "permissions"]
)
def test_untrusted_evidence_cannot_publish_verified_state(
    evidence: Any, fault: str, tmp_path: Path
) -> None:
    payload, sign, receipt, original, registry, config = evidence
    if fault == "signature":
        content = json.loads(receipt.read_text())
        content["payload"]["checks"][0]["expires_at"] = 9999
        receipt.write_text(json.dumps(content))
    elif fault == "field":
        config["producers"][0]["fields"] = ["target_writer_ref"]
        registry.write_text(json.dumps(config))
    elif fault == "value":
        payload["checks"][0]["value_sha256"] = "c" * 64
        sign()
    elif fault == "duplicate":
        payload["checks"].append(payload["checks"][0])
        sign()
    elif fault == "symlink":
        link = tmp_path / "link"
        link.symlink_to(original)
        payload["checks"][0]["evidence_file"] = str(link)
        sign()
    else:
        original.chmod(0o666)
    assert read()["source_writer_ref"]["state"] == "unavailable"


def test_context_roundtrip_is_revisioned_and_legacy_reads_stay_compatible(
    campaign: Campaign,
) -> None:
    c = campaign
    app = OperatorInputs(c.service)
    body = {
        "values": {"max_data_loss_bytes": 0},
        "configuration_digest": None,
        "context": {"operation": "migrate", "method": "VM_COLD_EXPORT"},
    }
    key = uid()
    saved = app.command(c.actor, "operator_readiness_save", body, key)
    assert app.command(c.actor, "operator_readiness_save", body, key) == saved
    view = app.readiness(c.actor)
    assert view["context"] == body["context"]
    assert "delta_ref" not in view["missing_fields"]
    assert "delta_ref" in app.read(c.actor)["missing_fields"]
    assert view["native_write_authorized"] is False
    assert view["evidence_current"] is False
    assert "environment_review_required" in view["holds"]
    assert "context" not in app.read(c.actor)["record"]
    with pytest.raises(Rejected, match="idempotency_conflict"):
        app.command(
            c.actor,
            "operator_readiness_save",
            {**body, "context": {"operation": "provision", "method": None}},
            key,
        )


def test_owner_publication_checks_the_packet_and_preserves_original_observations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tenant, site = uid(), uid()
    values = {"source_writer_ref": "secret:source"}
    context = {"operation": "migrate", "method": "VM_COLD_EXPORT"}
    bound = digest(
        [tenant, site, 1, {"values": values, "configuration_digest": "b" * 64, "context": context}]
    )
    packet: dict[str, Any] = {
        "tenant_id": tenant,
        "site_id": site,
        "native_write_authorized": False,
        "context": context,
        "record": {
            "revision": 1,
            "values": values,
            "configuration_digest": "b" * 64,
            "digest": bound,
        },
    }
    proof = tmp_path / "original.json"
    proof.write_bytes(b'{"synthetic":true,"observed":true}')
    proof.chmod(0o600)
    report = {
        "schema_version": 1,
        "producer_id": "platform-owner",
        "tenant_id": tenant,
        "site_id": site,
        "packet_digest": bound,
        "configuration_digest": "b" * 64,
        "checks": [
            {
                "field_id": "source_writer_ref",
                "value_sha256": digest(values["source_writer_ref"]),
                "result": "verified",
                "observed_at": 100,
                "expires_at": 200,
                "evidence_file": str(proof),
                "evidence_sha256": hashlib.sha256(proof.read_bytes()).hexdigest(),
            }
        ],
    }
    private = Ed25519PrivateKey.generate()
    key = tmp_path / "owner.key"
    key.write_bytes(private.private_bytes_raw())
    key.chmod(0o600)
    packet_file, report_file, receipt = (
        tmp_path / name for name in ("packet.json", "report.json", "signed.json")
    )
    for path, value in ((packet_file, packet), (report_file, report)):
        path.write_text(canonical(value))
        path.chmod(0o600)
    args = (str(packet_file), str(report_file), "platform-owner", str(key), str(receipt))
    publish(*args)
    assert receipt.stat().st_mode & 0o777 == 0o600
    assert json.loads(receipt.read_text())["payload"] == report
    registry = tmp_path / "registry.json"
    registry.write_text(
        canonical(
            {
                "schema_version": 1,
                "producers": [
                    {
                        "id": "platform-owner",
                        "public_key": base64.b64encode(
                            private.public_key().public_bytes_raw()
                        ).decode(),
                        "expires_at": 300,
                        "fields": ["source_writer_ref"],
                        "scopes": [{"tenant_id": tenant, "site_id": site}],
                        "receipts": [str(receipt)],
                    }
                ],
            }
        )
    )
    registry.chmod(0o600)
    monkeypatch.setenv("INVENTORY_COMMISSIONING_EVIDENCE_FILE", str(registry))
    assert (
        read_evidence(tenant, site, bound, "b" * 64, values, 150)["source_writer_ref"]["state"]
        == "verified"
    )
    with pytest.raises(FileExistsError):
        publish(*args)
    packet["record"]["values"]["source_writer_ref"] = "secret:changed"
    packet_file.write_text(canonical(packet))
    with pytest.raises(ValueError, match="input_packet_binding_changed"):
        publish(*args)


def test_producer_is_enrolled_for_the_exact_tenant_and_site(evidence: Any) -> None:
    payload, sign, _, _, registry, config = evidence
    payload["tenant_id"] = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    sign()
    assert read(tenant=payload["tenant_id"]) == {}
    config["producers"][0]["scopes"].append(
        {"tenant_id": payload["tenant_id"], "site_id": payload["site_id"]}
    )
    registry.write_text(canonical(config))
    assert read(tenant=payload["tenant_id"])["source_writer_ref"]["state"] == "verified"
    config["producers"].append({**config["producers"][0], "id": "different-owner-same-key"})
    registry.write_text(canonical(config))
    assert read(tenant=payload["tenant_id"])["source_writer_ref"]["state"] == "unavailable"
