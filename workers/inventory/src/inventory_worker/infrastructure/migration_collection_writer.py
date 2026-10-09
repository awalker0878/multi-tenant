"""Native GET → signed per-field evidence → Inventory durable ingestion.

No field is promoted from a Catalogue declaration, operator text, generated
crosswalk, or missing API response. A separate installed collector signing
key attests scoped GET outcomes, not native E3/E4 effect qualification.
"""
import base64
import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HEX = re.compile(r"^[a-f0-9]{64}$")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def capture_field(
    requirement: dict[str, Any], witness: dict[str, Any],
    installed_namespaces: dict[str, list[str]],
) -> dict[str, Any] | None:
    """Only a read witness of this exact declared native field creates a fact.

    The caller records the actual response value and native HTTP operation
    from its controlled request hook; missing/unknown/failed reads return
    None and are later held by Inventory's field coverage evaluator.
    """
    if (requirement.get("collection_method") != "native_get"
            or requirement.get("collection_status") == "external_evidence_required"
            or witness.get("attribute_id") != requirement.get("id")
            or witness.get("api_field") != requirement.get("api_field")
            or witness.get("api_family") != requirement.get("api_family")
            or not isinstance(witness.get("api_version"), str)
            or witness["api_version"] not in
               installed_namespaces.get(requirement["api_family"], [])
            or witness.get("status") != "read_success"
            or not isinstance(witness.get("native_operation"), str)
            or not re.fullmatch(r"GET /[A-Za-z0-9_./:%?=&-]{1,400}",
                                witness["native_operation"])
            or "value" not in witness or witness["value"] is None
            or type(witness.get("observed_at")) is not int):
        return None
    required = ("scope", "installation_id", "generation_id",
                "installed_tuple_sha256")
    if any(not isinstance(witness.get(k), str) or not witness[k]
           for k in required):
        return None
    if not HEX.fullmatch(witness["installed_tuple_sha256"]):
        return None
    value_sha = digest(witness["value"])
    proof = {
        "attribute_id": requirement["id"],
        **{k: witness[k] for k in required},
        "collection_method": "native_get",
        "api_family": witness["api_family"],
        "api_version": witness["api_version"],
        "native_operation": witness["native_operation"],
        "value_sha256": value_sha,
        "observed_at": witness["observed_at"],
        "value_present": True,
    }
    proof["evidence_sha256"] = digest(proof)
    return proof


def build_signed_envelope(
    manifest: dict[str, Any],
    scope: dict[str, str],
    signed_scopes: list[dict[str, Any]],
    expires_at: int, private_key_bytes: bytes,
) -> dict[str, Any]:
    """Signer must be mounted in an independently administered worker pod.

    All three scopes are explicit even when an attribute is unobserved.
    Owner evidence and conditional applicability are never synthesized.
    """
    if (manifest.get("schema_version") != 1
            or not isinstance(signed_scopes, list)
            or len(signed_scopes) != 3
            or {r.get("scope") for r in signed_scopes} !=
               {"source", "target", "owner"}
            or type(expires_at) is not int
            or len(private_key_bytes) != 32
            or set(scope) != {"tenant_id", "site_id",
                              "source_profile_sha256", "target_profile_sha256"}
            or any(not isinstance(v, str) or not v for v in scope.values())):
        raise ValueError("migration_collection_signing_input_invalid")
    for item in signed_scopes:
        platform = item.get("platform")
        if platform not in manifest["platforms"]:
            raise ValueError("unregistered_collection_platform")
        allowed = {entry["id"] for entry in manifest["platforms"][platform]["attributes"]
                   if entry["scope"] == item["scope"]}
        if (set(item) != {"scope", "platform", "installation_id",
                          "generation_id", "installed_tuple_sha256",
                          "observations", "applicability"}
                or any(not isinstance(items, list) or len(items) > 512
                       or any(not isinstance(row, dict)
                              or row.get("attribute_id") not in allowed
                              for row in items)
                       for items in (item["observations"], item["applicability"]))):
            raise ValueError("unsigned_or_out_of_scope_collection_fields")
    payload = {"schema_version": 1, **scope, "expires_at": expires_at,
               "scopes": signed_scopes}
    message = b"multi-tenant/migration-collection-evidence/v1\x00" + canonical(payload)
    signature = Ed25519PrivateKey.from_private_bytes(private_key_bytes).sign(message)
    return {"payload": payload,
            "signature": base64.b64encode(signature).decode("ascii")}


def publish(
    envelope: dict[str, Any], tenant: str, site: str,
    source_profile_id: str, target_profile_id: str,
    send: Callable[[str, dict[str, Any]], Any],
) -> Any:
    """Use worker-authenticated POST; no direct database connection."""
    return send("/internal/collections/receipts", {
        "tenant_id": tenant, "site_id": site,
        "source_profile_id": source_profile_id,
        "target_profile_id": target_profile_id,
        "envelope": envelope,
    })
