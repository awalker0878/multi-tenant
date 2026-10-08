"""E2 crypto controls; a native principal remains a commissioning prerequisite."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from lifecycle_worker.application.native import NativeHeld, digest
from lifecycle_worker.domain.capability_definitions import DEFINITION_SHA256, DIMENSIONS
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
    observed: dict[str, Any] = {
        "scope_sha256": digest(scope),
        "definition_sha256": DEFINITION_SHA256,
        "installed_tuple": scope["installed_tuple"],
        "observed_at": 1000,
        "cases": cases,
        "capabilities": {},
        "inventory": {},
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
    artifact.write_text("drift")
    publisher.publish(assignment | {"decision_sha256": "b" * 64})
    assert "b" * 64 in json.loads(output.read_text())["suspended"]
