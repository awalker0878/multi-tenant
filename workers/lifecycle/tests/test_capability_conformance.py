"""E2 crypto controls; a native principal remains a commissioning prerequisite."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from lifecycle_worker.application.native import NativeHeld, digest
from lifecycle_worker.domain.capability_definitions import (
    DEFINITION_SHA256,
    DIMENSIONS,
    MODES,
    WIRE_METHODS,
)
from lifecycle_worker.infrastructure.capability_conformance import ConformancePublisher


def test_failure_suspends_review_until_a_new_decision(tmp_path: Path) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = tmp_path / "key.pem"
    private.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    private.chmod(0o600)
    artifact = tmp_path / "adapter"
    artifact.write_text("actual-mounted-artifact")
    import hashlib

    artifacts = {"adapter": hashlib.sha256(artifact.read_bytes()).hexdigest()}
    scope = {"artifacts": artifacts, "installed_tuple": {"platform": "synthetic"}}
    cases = {
        name: {
            "outcome": "passed",
            "scope_sha256": digest(scope),
            "artifacts": artifacts,
            "observed_at": 1000,
        }
        for name in (
            "adapter_behavior",
            "installed_identity",
            "runtime_artifacts",
            *("dimension:" + d for d in DIMENSIONS),
        )
    }
    method_modes = {
        "method:" + method + ":" + mode: "unsupported" for method in WIRE_METHODS for mode in MODES
    }
    cases.update(
        {
            key: {
                "outcome": "unsupported",
                "reason": "not_qualified_on_synthetic_installation",
                "scope_sha256": digest(scope),
                "artifacts": artifacts,
                "observed_at": 1000,
            }
            for key in method_modes
        }
    )
    observed: dict[str, Any] = {
        "scope_sha256": digest(scope),
        "definition_sha256": DEFINITION_SHA256,
        "installed_tuple": scope["installed_tuple"],
        "observed_at": 1000,
        "cases": cases,
        "method_modes": method_modes,
        "capabilities": {},
        "inventory": {"installed_tuple": scope["installed_tuple"]},
        "snapshot": {},
    }
    read = Mock(return_value=observed)
    assignment = {
        "scope": scope,
        "private_key_file": str(private),
        "artifact_files": {"adapter": str(artifact)},
        "subject_id": "observer",
        "key_id": "observer-key",
        "decision_sha256": "a" * 64,
        "native_probe": {},
    }
    output = tmp_path / "runtime.json"
    publisher = ConformancePublisher(output, lambda: 1000, read)
    publisher.publish(assignment)
    assert json.loads(output.read_text())["suspended"] == {}
    read.side_effect = NativeHeld("restore_failed")
    publisher.publish(assignment)
    read.side_effect = None
    publisher.publish(assignment)
    state = json.loads(output.read_text())
    assert state["suspended"] == {"a" * 64: "restore_failed"}
    import base64

    receipt = json.loads(base64.b64decode(state["records"]["a" * 64]["content_base64"]))
    assert receipt["adapter_conformant"] is False
    publisher.publish(assignment | {"decision_sha256": "b" * 64})
    state = json.loads(output.read_text())
    receipt = json.loads(base64.b64decode(state["records"]["b" * 64]["content_base64"]))
    assert receipt["adapter_conformant"] is True
    # A signed observation with one missing method/mode must never
    # masquerade as a qualified installed provider release.
    missing = next(iter(method_modes))
    original_method_case = observed["cases"].pop(missing)
    publisher.publish(assignment | {"decision_sha256": "c" * 64})
    state = json.loads(output.read_text())
    denied = json.loads(base64.b64decode(state["records"]["c" * 64]["content_base64"]))
    assert denied["adapter_conformant"] is False
    observed["cases"][missing] = original_method_case
    # A native observer cannot sign a passing installed recovery method while
    # returning an empty readback dataset. This must suspend that decision.
    recovery = "method:" + next(iter(WIRE_METHODS)) + ":rollback"
    observed["method_modes"][recovery] = "passed"
    observed["cases"][recovery]["outcome"] = "passed"
    observed["cases"][recovery].pop("reason", None)
    publisher.publish(assignment | {"decision_sha256": "d" * 64})
    state = json.loads(output.read_text())
    denied = json.loads(base64.b64decode(state["records"]["d" * 64]["content_base64"]))
    assert denied["adapter_conformant"] is False
    assert state["suspended"]["d" * 64] == "conformance_recovery_readback_required"
    observed["snapshot"] = {
        "recovery_measurements": [
            {
                "dataset_id": "observed-dataset",
                "sequence": 1,
                "outcome": "passed",
                "consistency_passed": True,
                "method": recovery.split(":")[1],
                "mode": "rollback",
                "scope_sha256": digest(scope),
                "artifacts": artifacts,
                "observed_at": 1000,
                "readback_sha256": "d" * 64,
            },
        ]
    }
    publisher.publish(assignment | {"decision_sha256": "e" * 64})
    state = json.loads(output.read_text())
    accepted = json.loads(base64.b64decode(state["records"]["e" * 64]["content_base64"]))
    assert accepted["adapter_conformant"] is True
    # A readback for one method cannot qualify a different method's rollback.
    another = "method:" + list(WIRE_METHODS)[1] + ":rollback"
    observed["method_modes"][another] = "passed"
    observed["cases"][another]["outcome"] = "passed"
    observed["cases"][another].pop("reason", None)
    publisher.publish(assignment | {"decision_sha256": "1" * 64})
    state = json.loads(output.read_text())
    assert state["suspended"]["1" * 64] == "conformance_recovery_readback_required"
    observed["snapshot"]["recovery_measurements"].append(
        observed["snapshot"]["recovery_measurements"][0]
        | {"method": another.split(":")[1], "dataset_id": "second-dataset"}
    )
    publisher.publish(assignment | {"decision_sha256": "2" * 64})
    state = json.loads(output.read_text())
    receipt = json.loads(base64.b64decode(state["records"]["2" * 64]["content_base64"]))
    assert receipt["adapter_conformant"] is True
    # Top-level native outcome and nested inventory cannot disagree about
    # the actual installed tuple, even with otherwise valid signed cases.
    observed["inventory"]["installed_tuple"] = {"platform": "foreign"}
    publisher.publish(assignment | {"decision_sha256": "f" * 64})
    state = json.loads(output.read_text())
    denied = json.loads(base64.b64decode(state["records"]["f" * 64]["content_base64"]))
    assert denied["adapter_conformant"] is False
    assert state["suspended"]["f" * 64] == "conformance_inventory_scope_changed"
    observed["inventory"]["installed_tuple"] = scope["installed_tuple"]
    artifact.write_text("drift")
    publisher.publish(assignment | {"decision_sha256": "b" * 64})
    assert "b" * 64 in json.loads(output.read_text())["suspended"]
