"""Signed Inventory collection receipts cannot be declared by Console or Planning."""

import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from inventory.domain.discovery import canonical, digest
from inventory.infrastructure import migration_collection_evidence as module


def specimen():
    secret = Ed25519PrivateKey.generate()
    key = secret.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    manifest = {"schema_version": 1, "platforms": {
        "ahv": {"attributes": [
            {"id": "source.identity", "scope": "source", "api_family": "vmm",
             "api_field": "data.extId", "owner_evidence_field": None,
             "collection_method": "native_get", "max_age_seconds": 60,
             "severity": "critical", "condition": "always",
             "collector_source": "test", "collection_status": "native_field_candidate"},
            {"id": "owner.intent", "scope": "owner", "api_family": None,
             "api_field": None, "owner_evidence_field": "intent",
             "collection_method": "independent", "max_age_seconds": 60,
             "severity": "critical", "condition": "always",
             "collector_source": "test", "collection_status": "external_evidence_required"},
        ]},
        "openstack": {"attributes": [
            {"id": "target.identity", "scope": "target", "api_family": "nova",
             "api_field": "server.id", "owner_evidence_field": None,
             "collection_method": "native_get", "max_age_seconds": 60,
             "severity": "critical", "condition": "always",
             "collector_source": "test", "collection_status": "native_field_candidate"},
        ]},
    }}
    source = {"generation_id": "src-gen", "current": True, "facts": {
        "platform": "ahv", "profile_type": "SourceWorkloadProfile",
        "installation_id": "src-install",
        "versions": {"vmm": "v4.3"},
    }}
    target = {"generation_id": "tgt-gen", "current": True, "facts": {
        "platform": "openstack", "profile_type": "TargetCapabilityProfile",
        "project_id": "tgt-install",
        "api_versions": {"nova": ["2.104"]},
    }}
    left = {"profile_sha256": digest("src"), "tuple_sha256": digest("src-tuple")}
    right = {"profile_sha256": digest("tgt"), "tuple_sha256": digest("tgt-tuple")}
    def evidence(attribute, side, installation, generation, tuple_sha, family, method):
        return {
            "attribute_id": attribute, "scope": side,
            "installation_id": installation, "generation_id": generation,
            "installed_tuple_sha256": tuple_sha,
            "collection_method": method, "api_family": family,
            "api_version": "2.104" if family == "nova" else "v4.3" if family else None,
            "observed_at": 90, "evidence_sha256": digest(attribute),
            "value_present": True,
            "native_operation": "GET /api/vmm/v4.3/config/resource" if family else None,
            "value_sha256": digest(attribute) if family else None,
            "independent_review": True,
        }
    scopes = []
    for side, platform, install, generation, bound, field, family, method in (
        ("source", "ahv", "src-install", "src-gen", left, "source.identity", "vmm", "native_get"),
        ("target", "openstack", "tgt-install", "tgt-gen", right, "target.identity", "nova", "native_get"),
        ("owner", "ahv", "src-install", "src-gen", left, "owner.intent", None, "independent"),
    ):
        scopes.append({
            "scope": side, "platform": platform,
            "installation_id": install, "generation_id": generation,
            "installed_tuple_sha256": bound["tuple_sha256"],
            "observations": [evidence(field, side, install, generation,
                                      bound["tuple_sha256"], family, method)],
            "applicability": [],
        })
    payload = {
        "schema_version": 1, "tenant_id": "tenant", "site_id": "site",
        "source_profile_sha256": left["profile_sha256"],
        "target_profile_sha256": right["profile_sha256"],
        "expires_at": 150, "scopes": scopes,
    }
    def signed():
        signature = secret.sign(
            b"multi-tenant/migration-collection-evidence/v1\x00"
            + canonical(payload).encode()
        )
        return {"payload": payload, "signature": base64.b64encode(signature).decode()}
    return manifest, source, target, left, right, key, signed, payload


def test_current_signed_complete_field_coverage(monkeypatch):
    manifest, source, target, left, right, key, signed, _ = specimen()
    config = {
        "schema_version": 1, "manifest_file": "/manifest",
        "manifest_sha256": digest(manifest), "public_key_file": "/key",
        "signed_receipt_file": "/receipt",
    }
    files = {
        "/trust": canonical(config).encode(), "/manifest": canonical(manifest).encode(),
        "/key": key, "/receipt": canonical(signed()).encode(),
    }
    monkeypatch.setenv("INVENTORY_MIGRATION_COLLECTION_TRUST_FILE", "/trust")
    monkeypatch.setattr(module, "protected", lambda p, n: files[p])
    assert [r["status"] for r in module.read_collection_coverages(
        "tenant", "site", source, target, left, right, 100
    )] == ["complete", "complete", "complete"]
    files["/receipt"] = files["/receipt"].replace(b"src-install", b"bad-install")
    assert module.read_collection_coverages(
        "tenant", "site", source, target, left, right, 100
    ) == []


def test_uncommissioned_or_expired_signature_held(monkeypatch):
    manifest, source, target, left, right, key, signed, payload = specimen()
    monkeypatch.delenv("INVENTORY_MIGRATION_COLLECTION_TRUST_FILE", raising=False)
    assert module.read_collection_coverages(
        "tenant", "site", source, target, left, right, 100
    ) == []
    payload["expires_at"] = 99
    assert payload["expires_at"] < 100
