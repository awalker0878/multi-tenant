"""Project only signed, fresh native observations from an independently enrolled observer."""

import base64
import hashlib
import json
import os
import re
import stat
import time
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from inventory.domain.capability_definitions import (
    DEFINITION_SHA256,
    DIMENSIONS,
    MODES,
    WIRE_METHODS,
)
from inventory.domain.discovery import Rejected


def checksum(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def scoped_recovery_readbacks(observed: dict[str, Any], now: int) -> bool:
    """A signed generic recovery does not qualify other installed methods."""
    matrix = observed["method_modes"]
    snapshot = observed.get("snapshot")
    if snapshot is None:
        return not any(
            status == "passed"
            and key.rsplit(":", 1)[-1] in {"rollback", "forward_recovery", "reverse_recovery"}
            for key, status in matrix.items()
        )
    if not isinstance(snapshot, dict):
        return False
    measurements = snapshot.get("recovery_measurements", [])
    if not isinstance(measurements, list):
        return False
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    for sample in measurements:
        if (
            not isinstance(sample, dict)
            or sample.get("method") not in WIRE_METHODS
            or sample.get("mode") not in MODES
            or not isinstance(sample.get("dataset_id"), str)
            or not 1 <= len(sample["dataset_id"]) <= 160
            or type(sample.get("sequence")) is not int
            or sample["sequence"] < 1
            or type(sample.get("observed_at")) is not int
            or not 0 <= now - sample["observed_at"] <= 60
            or sample.get("scope_sha256") != observed.get("scope_sha256")
            or sample.get("artifacts") != observed.get("runtime_artifacts")
            or not isinstance(sample.get("readback_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", sample["readback_sha256"]) is None
        ):
            return False
        key = (sample["method"], sample["mode"], sample["dataset_id"])
        prior = latest.get(key)
        if prior is not None and prior["sequence"] == sample["sequence"]:
            return False
        if prior is None or sample["sequence"] > prior["sequence"]:
            latest[key] = sample
    if any(
        row.get("outcome") != "passed" or row.get("consistency_passed") is not True
        for row in latest.values()
    ):
        return False
    for key, status in matrix.items():
        _, method, mode = key.split(":")
        if (
            status == "passed"
            and mode in {"rollback", "forward_recovery", "reverse_recovery"}
            and not any(k[:2] == (method, mode) for k in latest)
        ):
            return False
    return True


def protected_document(path: Path) -> dict[str, Any]:
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("protected_path_invalid")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
            raise ValueError("protected_file_invalid")
        raw = stream.read(2097153)
    if len(raw) > 2097152:
        raise ValueError("protected_file_bound")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("protected_document_invalid")
    return result


class MountedCapabilityObservations:
    def read(self, base: dict[str, Any]) -> dict[str, Any] | None:
        path = os.environ.get("INVENTORY_CAPABILITY_EVIDENCE_FILE")
        if not path:
            return None
        try:
            state = protected_document(Path(path))
            trust = protected_document(Path(os.environ["INVENTORY_CAPABILITY_TRUST_FILE"]))
            now = int(time.time())
            results = []
            method_keys = {
                "method:" + method + ":" + mode for method in WIRE_METHODS for mode in MODES
            }
            if state["schema_version"] != 1 or trust["schema_version"] != 1:
                raise ValueError
            for decision, envelope in state["records"].items():
                raw = base64.b64decode(envelope["content_base64"], validate=True)
                if len(raw) > 262144 or hashlib.sha256(raw).hexdigest() != envelope["sha256"]:
                    raise ValueError
                observed = json.loads(raw)
                inventory = observed.get("inventory", {})
                if any(
                    inventory.get(k) != base[k]
                    for k in (
                        "tenant_id",
                        "site_id",
                        "endpoint_id",
                        "generation_id",
                        "native_scope",
                    )
                ):
                    continue
                key = trust["keys"][envelope["key_id"]]
                public = serialization.load_pem_public_key(key["public_key_pem"].encode())
                if not isinstance(public, rsa.RSAPublicKey) or public.key_size < 2048:
                    raise ValueError
                public.verify(
                    base64.b64decode(envelope["signature_base64"], validate=True),
                    raw,
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                if (
                    key["role"] != "observer"
                    or key.get("revoked") is not False
                    or observed["subject_id"] != key["subject_id"]
                    or key["expires_at"] <= now
                    or any(
                        key["scope"].get(k) != base[k]
                        for k in ("tenant_id", "site_id", "endpoint_id")
                    )
                    or decision in state.get("suspended", {})
                    or observed["decision_sha256"] != decision
                    or observed["kind"] != "native_conformance"
                    or observed["simulation"] is not False
                    or observed["finalized"] is not True
                    or observed["adapter_conformant"] is not True
                    or observed["definition_sha256"] != DEFINITION_SHA256
                    or inventory["installed_tuple"] != base["installed_tuple"]
                    or type(observed["observed_at"]) is not int
                    or not 0 <= now - observed["observed_at"] <= 60
                    or not now < observed["expires_at"] <= observed["observed_at"] + 120
                    or observed["expires_at"] > key["expires_at"]
                    or set(observed["dimensions"]) != set(DIMENSIONS)
                    or any(
                        observed["cases"].get(name) != "passed"
                        for name in ("adapter_behavior", "installed_identity", "runtime_artifacts")
                    )
                    or any(observed["cases"].get("dimension:" + d) != "passed" for d in DIMENSIONS)
                    or not isinstance(observed.get("method_modes"), dict)
                    or set(observed["method_modes"]) != method_keys
                    or not scoped_recovery_readbacks(observed, now)
                    or any(
                        observed["method_modes"][name] not in {"passed", "unsupported"}
                        or observed["cases"].get(name) != observed["method_modes"][name]
                        for name in method_keys
                    )
                ):
                    raise ValueError
                results.append(
                    {
                        "inventory": inventory,
                        "definition_sha256": DEFINITION_SHA256,
                        "source_sha256": envelope["sha256"],
                        "decision_sha256": decision,
                        "scope_sha256": observed["scope_sha256"],
                        "observed_at": observed["observed_at"],
                        "expires_at": observed["expires_at"],
                        "data": observed["snapshot"],
                    }
                )
            if len(results) > 1:
                raise ValueError("capability_observation_conflict")
            return results[0] if results else None
        except (KeyError, TypeError, ValueError, OSError, InvalidSignature):
            raise Rejected("capability_observation_unavailable", 503) from None
