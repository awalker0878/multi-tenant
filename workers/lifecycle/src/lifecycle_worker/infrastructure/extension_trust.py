"""Ed25519 package admission with current protected trust, expiry and exact capabilities.

Packages describe statically installed adapters. Admission never imports Python from
an uploaded artifact and never grants native authority or publishes native support.
"""

import base64
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from lifecycle_worker.application.native import NativeHeld, decode, digest, identity, sha256
from lifecycle_worker.infrastructure.native_files import protected_read

DOMAIN = b"multi-tenant/adapter-package/v1\x00"
CONTRACTS = {"native_effect": "2", "expansion": "1", "journal": "1"}
BUILTINS = {"vmware-lifecycle-v1", "ahv-lifecycle-v1"}
TRIGGERS = {
    "artifact",
    "platform",
    "api",
    "backend",
    "guest",
    "method",
    "policy",
    "service",
    "topology",
    "recovery",
    "ownership",
    "expiry",
    "revocation",
}


def signing_bytes(manifest: dict[str, Any]) -> bytes:
    return (
        DOMAIN
        + json.dumps(
            manifest, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode()
    )


def implementation_digest() -> str:
    root = Path(__file__).resolve().parents[1]
    files = sorted(root.rglob("*.py"))
    if not 1 <= len(files) <= 512:
        raise NativeHeld("extension_implementation_bound")
    return digest(
        {
            str(p.relative_to(root)): hashlib.sha256(protected_read(p, 1048576)).hexdigest()
            for p in files
        }
    )


def shape(value: Any, keys: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise NativeHeld("invalid_extension_contract")


class ExtensionTrust:
    def __init__(self, trust_file: Path, clock: Callable[[], int]) -> None:
        self.trust_file, self.clock = trust_file, clock

    def admit(
        self, envelope_file: Path, artifact_file: Path, expected: str, capability: dict[str, str]
    ) -> dict[str, Any]:
        trust = decode(protected_read(self.trust_file, 262144))
        shape(trust, {"schema_version", "epoch", "expires_at", "keys", "revoked_artifacts"})
        envelope = decode(protected_read(envelope_file, 1048576))
        shape(envelope, {"manifest", "key_id", "signature"})
        m = envelope["manifest"]
        shape(
            m,
            {
                "schema_version",
                "adapter_id",
                "version",
                "artifact_sha256",
                "release_sha256",
                "contracts",
                "capabilities",
                "constraint_sha256",
                "not_before",
                "expires_at",
                "retest_triggers",
                "owner_role",
                "implementation_sha256",
            },
        )
        now = self.clock()
        if (
            trust["schema_version"] != 1
            or type(trust["schema_version"]) is not int
            or m["schema_version"] != 1
            or type(m["schema_version"]) is not int
            or not sha256(expected)
            or digest(m) != expected
            or m["adapter_id"] not in BUILTINS
            or m["contracts"] != CONTRACTS
        ):
            raise NativeHeld("extension_incompatible_or_changed")
        identity(trust["epoch"])
        for key in (
            "artifact_sha256",
            "release_sha256",
            "constraint_sha256",
            "implementation_sha256",
        ):
            if not sha256(m[key]):
                raise NativeHeld("invalid_extension_digest")
        for owner in (m["version"], m["owner_role"]):
            if (
                not isinstance(owner, str)
                or not 1 <= len(owner) <= 100
                or any(ord(c) < 32 for c in owner)
            ):
                raise NativeHeld("invalid_extension_metadata")
        times = [trust["expires_at"], m["not_before"], m["expires_at"]]
        if any(type(t) is not int for t in times) or not m["not_before"] <= now < min(
            m["expires_at"], trust["expires_at"]
        ):
            raise NativeHeld("extension_expired")
        if not isinstance(trust["revoked_artifacts"], list) or any(
            not sha256(v) for v in trust["revoked_artifacts"]
        ):
            raise NativeHeld("invalid_extension_revocation")
        if m["artifact_sha256"] in trust["revoked_artifacts"]:
            raise NativeHeld("extension_revoked")
        if (
            not isinstance(m["retest_triggers"], list)
            or len(m["retest_triggers"]) != len(TRIGGERS)
            or any(not isinstance(v, str) for v in m["retest_triggers"])
            or set(m["retest_triggers"]) != TRIGGERS
        ):
            raise NativeHeld("extension_retest_policy_required")
        if not isinstance(m["capabilities"], list) or not 1 <= len(m["capabilities"]) <= 512:
            raise NativeHeld("extension_capability_bound")
        seen = set()
        for cap in m["capabilities"]:
            shape(cap, {"operation", "tuple_sha256", "route_sha256"})
            if (
                cap["operation"]
                not in {"power_on", "shutdown", "power_off", "resize_cpu", "resize_memory"}
                or not sha256(cap["tuple_sha256"])
                or not sha256(cap["route_sha256"])
            ):
                raise NativeHeld("invalid_extension_capability")
            if digest(cap) in seen:
                raise NativeHeld("duplicate_extension_capability")
            seen.add(digest(cap))
        if capability not in m["capabilities"]:
            raise NativeHeld("extension_exact_capability_not_declared")
        if not isinstance(trust["keys"], list) or not 1 <= len(trust["keys"]) <= 64:
            raise NativeHeld("invalid_extension_keys")
        matches = [
            k for k in trust["keys"] if isinstance(k, dict) and k.get("id") == envelope["key_id"]
        ]
        if len(matches) != 1:
            raise NativeHeld("extension_key_untrusted")
        signer = matches[0]
        shape(signer, {"id", "public_key", "not_before", "expires_at", "revoked", "adapters"})
        if (
            signer["revoked"] is not False
            or type(signer["not_before"]) is not int
            or type(signer["expires_at"]) is not int
            or not signer["not_before"] <= now < signer["expires_at"]
            or not isinstance(signer["adapters"], list)
            or m["adapter_id"] not in signer["adapters"]
        ):
            raise NativeHeld("extension_key_untrusted")
        try:
            public = base64.b64decode(signer["public_key"], validate=True)
            signature = base64.b64decode(envelope["signature"], validate=True)
            Ed25519PublicKey.from_public_bytes(public).verify(signature, signing_bytes(m))
        except (ValueError, TypeError, InvalidSignature):
            raise NativeHeld("extension_signature_invalid") from None
        artifact = protected_read(artifact_file, 64 * 1024 * 1024)
        if hashlib.sha256(artifact).hexdigest() != m["artifact_sha256"]:
            raise NativeHeld("extension_artifact_changed")
        if implementation_digest() != m["implementation_sha256"]:
            raise NativeHeld("extension_installed_implementation_changed")
        if self.clock() >= min(m["expires_at"], trust["expires_at"], signer["expires_at"]):
            raise NativeHeld("extension_expired")
        return dict(m)


def upgrade(
    previous: dict[str, Any], candidate: dict[str, Any], proof: dict[str, Any], now: int
) -> None:
    """A trusted qualification owner supplies this transition proof, never the package."""
    shape(
        proof,
        {
            "from_sha256",
            "to_sha256",
            "active_attempts",
            "unknown_attempts",
            "common_paths_sha256",
            "recovery_sha256",
            "decision",
            "expires_at",
        },
    )
    if (
        proof["from_sha256"] != digest(previous)
        or proof["to_sha256"] != digest(candidate)
        or previous["adapter_id"] != candidate["adapter_id"]
        or candidate["contracts"] != CONTRACTS
        or proof["decision"] != "accepted"
        or proof["active_attempts"] != []
        or proof["unknown_attempts"] != []
        or type(proof["expires_at"]) is not int
        or proof["expires_at"] <= now
        or not all(sha256(proof[k]) for k in ("common_paths_sha256", "recovery_sha256"))
    ):
        raise NativeHeld("extension_transition_held")
