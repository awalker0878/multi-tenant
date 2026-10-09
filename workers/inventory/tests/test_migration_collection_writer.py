"""Field publication is limited to real native GET witnesses and signed scope."""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from inventory_worker.infrastructure.migration_collection_writer import (
    build_signed_envelope, canonical, capture_field, digest, publish,
)


def requirement() -> dict:
    return {
        "id": "identity.vm", "scope": "source", "collection_method": "native_get",
        "collection_status": "native_field_candidate", "api_family": "vmm",
        "api_field": "data.extId",
    }


def witness() -> dict:
    return {
        "attribute_id": "identity.vm", "scope": "source",
        "api_field": "data.extId", "api_family": "vmm",
        "api_version": "v4.3", "status": "read_success",
        "native_operation": "GET /api/vmm/v4.3/ahv/config/vms/123",
        "value": "native-vm", "observed_at": 100,
        "installation_id": "installation", "generation_id": "generation",
        "installed_tuple_sha256": digest("installed"),
    }


def test_native_get_only_signed_field_and_installed_namespace() -> None:
    proof = capture_field(requirement(), witness(), {"vmm": ["v4.3"]})
    assert proof is not None
    assert proof["value_sha256"] == digest("native-vm")
    assert proof["evidence_sha256"] == digest({
        k: v for k, v in proof.items() if k != "evidence_sha256"
    })
    for field, value in (
        ("status", "read_failed"), ("scope", "target"),
        ("api_version", "v4.2"), ("value", None),
        ("native_operation", "POST /api/vmm/v4.3/ahv/config/vms/123"),
    ):
        changed = witness() | {field: value}
        assert capture_field(requirement(), changed, {"vmm": ["v4.3"]}) is None
    assert capture_field(requirement(), witness(), {"vmm": ["v4.2"]}) is None


def test_signed_envelope_provides_exact_authority_custody_and_send() -> None:
    secret = Ed25519PrivateKey.generate()
    private = secret.private_bytes(serialization.Encoding.Raw,
                                   serialization.PrivateFormat.Raw,
                                   serialization.NoEncryption())
    manifest = {
        "schema_version": 1, "platforms": {
            "ahv": {"attributes": [requirement()]},
        },
    }
    signed_scopes = [
        {"scope": side, "platform": "ahv", "installation_id": "installation",
         "generation_id": "generation",
         "installed_tuple_sha256": digest("installed"),
         "observations": [capture_field(requirement(), witness(), {"vmm": ["v4.3"]})]
         if side == "source" else [],
         "applicability": []}
        for side in ("source", "target", "owner")
    ]
    envelope = build_signed_envelope(
        manifest, {"tenant_id": "tenant", "site_id": "site",
                   "source_profile_sha256": digest("source"),
                   "target_profile_sha256": digest("target")},
        signed_scopes, 160, private,
    )
    import base64
    secret.public_key().verify(
        base64.b64decode(envelope["signature"]),
        b"multi-tenant/migration-collection-evidence/v1\x00"
        + canonical(envelope["payload"]),
    )
    assert publish(envelope, "tenant", "site", "src", "tgt",
                   lambda path, body: (path, body["envelope"])) == (
        "/internal/collections/receipts", envelope,
    )
    signed_scopes[0]["observations"][0]["attribute_id"] = "foreign"
    import pytest
    with pytest.raises(ValueError, match="out_of_scope"):
        build_signed_envelope(
            manifest, {"tenant_id": "tenant", "site_id": "site",
                       "source_profile_sha256": digest("source"),
                       "target_profile_sha256": digest("target")},
            signed_scopes, 160, private,
        )
