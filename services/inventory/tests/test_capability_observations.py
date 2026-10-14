"""Signed projection binds the observed native identity and preserves discovery holds."""

import base64
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from inventory.application.capability_observations import capability_input
from inventory.domain.capability_definitions import (
    DEFINITION_SHA256,
    DIMENSIONS,
    MODES,
    WIRE_METHODS,
)
from inventory.domain.discovery import Rejected
from inventory.infrastructure.capability_observations import MountedCapabilityObservations


def test_projection_preserves_discovery_holds_and_expiry() -> None:
    base = {"holds": ["ownership_collision"], "expires_at": 1000}
    observed = {
        "inventory": {
            k: {}
            for k in (
                "dimensions",
                "capabilities",
                "capacity",
                "domain_bindings",
                "workload_bindings",
            )
        },
        "expires_at": 900,
    }
    with patch("inventory.application.capability_observations.planning_input", return_value=base):
        result = capability_input(
            Mock(), "t", "s", "e", "g", Mock(read=Mock(return_value=observed))
        )
    assert result["holds"] == ["ownership_collision"]
    assert result["expires_at"] == 900
    assert "inventory" in observed
    with patch(
        "inventory.application.capability_observations.planning_input",
        return_value={
            "holds": ["ownership_collision"],
            "expires_at": 1000,
        },
    ):
        repeated = capability_input(
            Mock(), "t", "s", "e", "g", Mock(read=Mock(return_value=observed))
        )
    assert repeated["capability_snapshot"] == result["capability_snapshot"]
    assert "inventory" in observed


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "signature",
        "expired",
        "tuple",
        "suspended",
        "missing_method",
        "false_method",
        "revoked",
        "missing_revocation",
        "missing_core_case",
        "passed_recovery_missing_readback",
        "passed_recovery_foreign_readback",
        "passed_recovery_valid",
        "passed_recovery_duplicate_old_sequence",
    ],
)
def test_signed_observation_is_not_an_adapter_assertion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    now = int(time.time())
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    base: dict[str, Any] = {
        k: k for k in ("tenant_id", "site_id", "endpoint_id", "generation_id", "native_scope")
    }
    base["installed_tuple"] = {"platform": "synthetic"}
    method_modes = {
        "method:" + method + ":" + mode: "unsupported" for method in WIRE_METHODS for mode in MODES
    }
    payload: dict[str, Any] = {
        "inventory": base,
        "subject_id": "observer",
        "decision_sha256": "a" * 64,
        "kind": "native_conformance",
        "simulation": False,
        "finalized": True,
        "adapter_conformant": True,
        "definition_sha256": DEFINITION_SHA256,
        "scope_sha256": "b" * 64,
        "runtime_artifacts": {"adapter": "c" * 64},
        "observed_at": now,
        "expires_at": now + 30,
        "dimensions": list(DIMENSIONS),
        "cases": {
            **{
                name: "passed"
                for name in ("adapter_behavior", "installed_identity", "runtime_artifacts")
            },
            **{"dimension:" + d: "passed" for d in DIMENSIONS},
            **method_modes,
        },
        "method_modes": method_modes,
        "snapshot": {},
    }
    if fault == "expired":
        payload["expires_at"] = now - 1
    if fault == "tuple":
        payload["inventory"] = base | {"installed_tuple": {"platform": "changed"}}
    if fault == "missing_method":
        payload["method_modes"].pop(next(iter(method_modes)))
    if fault == "false_method":
        payload["method_modes"][next(iter(method_modes))] = "passed"
    if fault == "missing_core_case":
        payload["cases"].pop("installed_identity")
    if fault.startswith("passed_recovery_"):
        method = next(iter(WIRE_METHODS))
        recovery_key = "method:" + method + ":rollback"
        payload["method_modes"][recovery_key] = "passed"
        payload["cases"][recovery_key] = "passed"
        if fault != "passed_recovery_missing_readback":
            payload["snapshot"] = {
                "recovery_measurements": [
                    {
                        "method": (
                            list(WIRE_METHODS)[1]
                            if fault == "passed_recovery_foreign_readback"
                            else method
                        ),
                        "mode": "rollback",
                        "dataset_id": "dataset-1",
                        "sequence": 1,
                        "observed_at": now,
                        "scope_sha256": payload["scope_sha256"],
                        "artifacts": payload["runtime_artifacts"],
                        "readback_sha256": "d" * 64,
                        "outcome": "passed",
                        "consistency_passed": True,
                    }
                ]
            }
    if fault == "passed_recovery_duplicate_old_sequence":
        first = payload["snapshot"]["recovery_measurements"][0]
        payload["snapshot"]["recovery_measurements"].extend([first | {"sequence": 2}, dict(first)])
    raw = json.dumps(payload).encode()
    import hashlib

    envelope = {
        "key_id": "observer-key",
        "content_base64": base64.b64encode(raw).decode(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "signature_base64": base64.b64encode(
            key.sign(raw, padding.PKCS1v15(), hashes.SHA256())
        ).decode(),
    }
    if fault == "signature":
        envelope["signature_base64"] = base64.b64encode(b"wrong").decode()
    evidence = tmp_path / "runtime.json"
    trust = tmp_path / "trust.json"
    evidence.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "records": {"a" * 64: envelope},
                "suspended": {"a" * 64: "failed"} if fault == "suspended" else {},
            }
        )
    )
    trust.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "keys": {
                    "observer-key": {
                        "role": "observer",
                        "subject_id": "observer",
                        **(
                            {} if fault == "missing_revocation" else {"revoked": fault == "revoked"}
                        ),
                        "public_key_pem": key.public_key()
                        .public_bytes(
                            serialization.Encoding.PEM,
                            serialization.PublicFormat.SubjectPublicKeyInfo,
                        )
                        .decode(),
                        "expires_at": now + 600,
                        "scope": {k: base[k] for k in ("tenant_id", "site_id", "endpoint_id")},
                    }
                },
            }
        )
    )
    monkeypatch.setenv("INVENTORY_CAPABILITY_EVIDENCE_FILE", str(evidence))
    monkeypatch.setenv("INVENTORY_CAPABILITY_TRUST_FILE", str(trust))
    owner = MountedCapabilityObservations()
    if fault in ("none", "passed_recovery_valid"):
        assert owner.read(base) is not None
    else:
        with pytest.raises(Rejected, match="capability_observation_unavailable"):
            owner.read(base)
