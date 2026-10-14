"""Read independent native probes and publish current signed results, never qualification."""

import base64
import fcntl
import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from lifecycle_worker.application.native import NativeHeld, decode, digest
from lifecycle_worker.domain.capability_definitions import (
    DEFINITION_SHA256,
    DIMENSIONS,
    MODES,
    WIRE_METHODS,
)
from lifecycle_worker.infrastructure.evidence_probes import ProbeJson, fresh_measurement, matches
from lifecycle_worker.infrastructure.native_files import protected_read


def read_probe(probe: dict[str, Any], now: int) -> dict[str, Any]:
    predicates = probe["predicates"]
    if not fresh_measurement(predicates, "/observed_at"):
        raise NativeHeld("conformance_measurement_freshness_required")
    api = ProbeJson(probe["connection"])
    api.verify(lambda: None)
    result = api.request("GET", probe["path"], lambda: None)
    if not isinstance(result, dict) or not all(matches(result, p, now) for p in predicates):
        raise NativeHeld("conformance_native_outcome_failed")
    return result


class ConformancePublisher:
    def __init__(
        self,
        output: Path,
        clock: Callable[[], int],
        read: Callable[[dict[str, Any], int], dict[str, Any]] = read_probe,
    ) -> None:
        self.output, self.clock, self.read = output, clock, read

    def publish(self, assignment: dict[str, Any]) -> dict[str, Any]:
        scope, now = assignment["scope"], self.clock()
        private = serialization.load_pem_private_key(
            protected_read(Path(assignment["private_key_file"]), 16384), password=None
        )
        if not isinstance(private, rsa.RSAPrivateKey) or private.key_size < 2048:
            raise NativeHeld("conformance_key_invalid")
        artifacts: dict[str, str] = {}
        reason = ""
        payload: dict[str, Any] = {
            "kind": "native_conformance",
            "subject_id": assignment["subject_id"],
            "scope_sha256": digest(scope),
            "definition_sha256": DEFINITION_SHA256,
            "decision_sha256": assignment["decision_sha256"],
            "observed_at": now,
            "expires_at": now + 30,
            "simulation": False,
            "finalized": True,
            "adapter_conformant": False,
            "runtime_artifacts": artifacts,
            "cases": {},
        }
        try:
            if set(assignment["artifact_files"]) != set(scope["artifacts"]):
                raise NativeHeld("conformance_artifact_manifest_changed")
            for name, path in assignment["artifact_files"].items():
                artifacts[name] = hashlib.sha256(protected_read(Path(path), 16777216)).hexdigest()
            if artifacts != scope["artifacts"]:
                raise NativeHeld("conformance_runtime_artifact_changed")
            observed = self.read(assignment["native_probe"], now)
            if (
                observed["scope_sha256"] != digest(scope)
                or observed["definition_sha256"] != DEFINITION_SHA256
                or observed["installed_tuple"] != scope["installed_tuple"]
                or type(observed["observed_at"]) is not int
                or not 0 <= now - observed["observed_at"] <= 30
            ):
                raise NativeHeld("conformance_native_scope_changed")
            required = {"adapter_behavior", "installed_identity", "runtime_artifacts"}
            required.update("dimension:" + d for d in DIMENSIONS)
            required.update("capability:" + c for c in observed["capabilities"])
            # Every active wire method and recovery mode is assessed for the
            # EXACT installed tuple. Unsupported is an explicit negative
            # outcome, never a qualified capability or inherited E2 result.
            method_keys = {
                "method:" + method + ":" + mode
                for method in WIRE_METHODS for mode in MODES
            }
            declared_method_modes = observed["method_modes"]
            if (not isinstance(declared_method_modes, dict)
                    or set(declared_method_modes) != method_keys):
                raise NativeHeld("installed_method_mode_matrix_incomplete")
            cases = observed["cases"]
            for name in required:
                case = cases.get(name, {})
                if (
                    case.get("outcome") != "passed"
                    or case.get("scope_sha256") != digest(scope)
                    or case.get("artifacts") != artifacts
                    or type(case.get("observed_at")) is not int
                    or not 0 <= now - case["observed_at"] <= 30
                ):
                    raise NativeHeld("conformance_native_case_failed")
                if name.startswith("capability:") and case.get("values_sha256") != digest(
                    observed["capabilities"][name[11:]]["values"]
                ):
                    raise NativeHeld("conformance_native_values_changed")
            method_modes: dict[str, str] = {}
            for name in sorted(method_keys):
                case = cases.get(name, {})
                outcome = case.get("outcome") if isinstance(case, dict) else None
                if (outcome not in {"passed", "unsupported"}
                        or declared_method_modes[name] != outcome
                        or case.get("scope_sha256") != digest(scope)
                        or case.get("artifacts") != artifacts
                        or type(case.get("observed_at")) is not int
                        or not 0 <= now - case["observed_at"] <= 30):
                    raise NativeHeld("installed_method_mode_not_observed")
                if outcome == "unsupported" and (
                    not isinstance(case.get("reason"), str)
                    or not 1 <= len(case["reason"]) <= 160
                ):
                    raise NativeHeld("installed_method_mode_unsupported_reason_required")
                method_modes[name] = outcome
            latest_restores: dict[str, dict[str, Any]] = {}
            for sample in observed["snapshot"].get("recovery_measurements", []):
                prior = latest_restores.get(sample["dataset_id"])
                if prior is None or sample["sequence"] > prior["sequence"]:
                    latest_restores[sample["dataset_id"]] = sample
            # A qualified rollback/recovery outcome must include at least
            # one fresh independent restoration/readback measurement. An
            # empty recovery report must never qualify a recovery mode.
            if not latest_restores and any(
                outcome == "passed" and name.rsplit(":", 1)[-1] in {
                    "rollback", "forward_recovery", "reverse_recovery"
                }
                for name, outcome in method_modes.items()
            ):
                raise NativeHeld("conformance_recovery_readback_required")
            if any(
                r["outcome"] != "passed" or r["consistency_passed"] is not True
                for r in latest_restores.values()
            ):
                raise NativeHeld("conformance_latest_restore_failed")
            payload.update(
                adapter_conformant=True,
                dimensions=list(DIMENSIONS),
                capabilities=observed["capabilities"],
                inventory=observed["inventory"],
                snapshot=observed["snapshot"],
                method_modes=method_modes,
                cases={**{name: "passed" for name in required}, **method_modes},
                observed_at=observed["observed_at"],
                expires_at=observed["observed_at"] + 30,
            )
        except (NativeHeld, KeyError, TypeError, ValueError, OSError) as error:
            reason = str(error)
        output = self.output
        if not output.is_absolute() or any(p.is_symlink() for p in (output, *output.parents)):
            raise NativeHeld("conformance_output_invalid")
        lock = output.with_suffix(".lock")
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+") as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            state: dict[str, Any] = (
                decode(protected_read(output, 2097152))
                if output.exists()
                else {"schema_version": 1, "records": {}, "suspended": {}, "revision": 0}
            )
            if state.get("schema_version") != 1 or len(state["records"]) > 256:
                raise NativeHeld("conformance_registry_invalid")
            decision = assignment["decision_sha256"]
            if reason:
                state["suspended"][decision] = reason
            if decision in state["suspended"]:
                payload["adapter_conformant"] = False
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            envelope = {
                "key_id": assignment["key_id"],
                "content_base64": base64.b64encode(raw).decode(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "signature_base64": base64.b64encode(
                    private.sign(raw, padding.PKCS1v15(), hashes.SHA256())
                ).decode(),
            }
            state["records"][decision] = envelope
            state["revision"] += 1
            raw_state = json.dumps(state, sort_keys=True, separators=(",", ":"))
            if len(raw_state.encode()) > 2097152:
                raise NativeHeld("conformance_registry_bound")
            temporary, path = tempfile.mkstemp(prefix=".conformance-", dir=output.parent)
            try:
                with os.fdopen(temporary, "w") as stream:
                    stream.write(raw_state)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(path, output)
            finally:
                if os.path.exists(path):
                    os.unlink(path)
            return envelope
