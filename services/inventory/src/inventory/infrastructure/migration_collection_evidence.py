"""Independently signed, per-field Inventory migration collection evidence.

The collection manifest is a declaration. A mounted signed receipt is evidence
only if the independent collector binds every attribute, installed tuple, native
generation, tenant/site, and exact profile digests. This reader grants no E3/E4
support and never creates missing observations.
"""

import base64
import hashlib
import os
import re
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from inventory.domain.discovery import Rejected, canonical, digest, shape
from inventory.domain.migration_collection_coverage import evaluate
from inventory.infrastructure.native_readers import decode, protected


def _profile_environment(profile: dict[str, Any], bound: dict[str, Any]) -> dict[str, Any]:
    facts = profile["facts"]
    if facts["profile_type"] == "SourceWorkloadProfile":
        installation = facts.get("installation_id", facts.get("vcenter_uuid"))
    else:
        installation = (
            facts.get("prism_central_id")
            or facts.get("vcenter_uuid")
            or facts.get("project_id")
        )
    return {
        "profile_sha256": bound["profile_sha256"],
        "platform": facts["platform"],
        "installation_id": installation,
        "generation_id": profile["generation_id"],
        "installed_tuple_sha256": bound["tuple_sha256"],
        # Only independently captured installed namespace releases may
        # authorize field receipts; an arbitrary receipt string never does.
        "installed_namespaces": {
            family: [version] if isinstance(version, str) else version
            for family, version in (
                facts.get("versions") or facts.get("api_versions") or {}
            ).items()
            if isinstance(family, str)
            and (isinstance(version, str)
                 or isinstance(version, list)
                 and all(isinstance(v, str) for v in version))
        },
    }


def read_collection_coverages(
    tenant: str, site: str, source: dict[str, Any], target: dict[str, Any],
    source_binding: dict[str, Any], target_binding: dict[str, Any], now: int,
    signed_envelope: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return 3 complete independently observed scopes, else no approvals.

    Configuration and public key are installed by infrastructure operators,
    not a request. Reader failures are unavailable evidence, never eligibility.
    """
    location = os.environ.get("INVENTORY_MIGRATION_COLLECTION_TRUST_FILE")
    if not location:
        return []
    try:
        config = decode(protected(location, 16384))
        shape(config, {
            "schema_version", "manifest_file", "manifest_sha256",
            "public_key_file", "signed_receipt_file",
        })
        if config["schema_version"] != 1 or not re.fullmatch(
            r"[a-f0-9]{64}", config["manifest_sha256"]
        ):
            raise ValueError
        manifest_raw = protected(config["manifest_file"], 262144)
        manifest = decode(manifest_raw)
        if (digest(manifest) != config["manifest_sha256"]
                or manifest.get("schema_version") != 1):
            raise ValueError
        key = Ed25519PublicKey.from_public_bytes(protected(config["public_key_file"], 32))
        # A durable SQL-custodied envelope is verified with the same
        # installed public key and scope rules as the mounted bootstrap file.
        envelope = (
            signed_envelope if signed_envelope is not None
            else decode(protected(config["signed_receipt_file"], 524288))
        )
        shape(envelope, {"payload", "signature"})
        signature = base64.b64decode(envelope["signature"], validate=True)
        payload = envelope["payload"]
        key.verify(
            signature,
            b"multi-tenant/migration-collection-evidence/v1\x00" + canonical(payload).encode(),
        )
        shape(payload, {
            "schema_version", "tenant_id", "site_id",
            "source_profile_sha256", "target_profile_sha256",
            "expires_at", "scopes",
        })
        left = _profile_environment(source, source_binding)
        right = _profile_environment(target, target_binding)
        if (
            type(payload["schema_version"]) is not int or payload["schema_version"] != 1
            or payload["tenant_id"] != tenant or payload["site_id"] != site
            or payload["source_profile_sha256"] != left["profile_sha256"]
            or payload["target_profile_sha256"] != right["profile_sha256"]
            or type(payload["expires_at"]) is not int or payload["expires_at"] <= now
            or source.get("current") is not True
            or target.get("current") is not True
            or not isinstance(payload["scopes"], list)
            or len(payload["scopes"]) != 3
        ):
            raise ValueError
        scopes: dict[str, dict[str, Any]] = {}
        for receipt in payload["scopes"]:
            shape(receipt, {
                "scope", "platform", "installation_id", "generation_id",
                "installed_tuple_sha256", "observations", "applicability",
            })
            side = receipt["scope"]
            expectation = right if side == "target" else left
            if (
                side not in {"source", "target", "owner"} or side in scopes
                or any(receipt.get(k) != expectation.get(k)
                       for k in ("platform", "installation_id", "generation_id",
                                 "installed_tuple_sha256"))
            ):
                raise ValueError
            scopes[side] = receipt
        if set(scopes) != {"source", "target", "owner"}:
            raise ValueError
        output = []
        for side in ("source", "target", "owner"):
            record = scopes[side]
            expectation = right if side == "target" else left
            result = evaluate(
                manifest, record["platform"], side,
                record["installation_id"], record["generation_id"],
                record["installed_tuple_sha256"],
                record["observations"], record["applicability"], now,
                installed_namespaces=expectation["installed_namespaces"],
                receipt_expires_at=payload["expires_at"],
            )
            # Presence of a well-formed signed file does not prove coverage.
            # All manifest attributes must be represented by fresh, correctly
            # sourced field-level evidence, including conditional applicability.
            output.append(result)
        return output
    except Exception:
        return []
