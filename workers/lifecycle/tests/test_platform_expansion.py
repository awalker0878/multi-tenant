"""Real signatures plus synthetic native peers; no installed platform is qualified."""

import base64
import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from lifecycle_worker.application.native import (
    NativeApiExecution,
    NativeBinding,
    NativeHeld,
    digest,
)
from lifecycle_worker.application.platform_plan import achieved, request, validate
from lifecycle_worker.infrastructure.extension_trust import (
    CONTRACTS,
    TRIGGERS,
    ExtensionTrust,
    implementation_digest,
    signing_bytes,
    upgrade,
)
from lifecycle_worker.infrastructure.platform_api import PlatformApi, PlatformObserver


def write(path: Path, value: Any) -> Path:
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return path


def binding() -> NativeBinding:
    return NativeBinding.parse(
        {k: str(uuid4()) for k in NativeBinding.__dataclass_fields__}
        | {
            "plan_digest": "a" * 64,
            "operation_plan_sha256": "b" * 64,
            "ownership_digest": "c" * 64,
            "custody_generation": 1,
            "expires_at": 200,
        }
    )


def plan_for(
    b: NativeBinding, platform: str = "vmware", op: str = "power_on"
) -> tuple[dict[str, Any], dict[str, Any]]:
    vm = "vm-42" if platform == "vmware" else str(uuid4())
    current = (
        {"power_state": "POWERED_OFF", "cpu": {"count": 2}, "memory": {"size_MiB": 2048}}
        if platform == "vmware"
        else {
            "extId": vm,
            "powerState": "OFF",
            "numSockets": 1,
            "numCoresPerSocket": 2,
            "memorySizeBytes": 2147483648,
            "nics": [{"network": "unchanged"}],
        }
    )
    return {
        "schema_version": 1,
        "platform": platform,
        "api_contract": "vcenter-rest-v1" if platform == "vmware" else "vmm-v4.0",
        **{
            k: b.document()[k]
            for k in ("project_id", "custody_id", "custody_generation", "ownership_digest")
        },
        "object_id": vm,
        "operation": op,
        "baseline_sha256": digest(current),
        "desired": {"count": 4}
        if op == "resize_cpu"
        else {"size_mib": 4096}
        if op == "resize_memory"
        else {},
        "tuple_sha256": "d" * 64,
        "route_sha256": "e" * 64,
        "adapter_sha256": "f" * 64,
    }, current


def signed(
    tmp_path: Path, plan: dict[str, Any]
) -> tuple[ExtensionTrust, Path, Path, dict[str, Any], dict[str, Any]]:
    key = Ed25519PrivateKey.generate()
    artifact = tmp_path / "adapter.whl"
    artifact.write_bytes(b"synthetic build artifact; never loaded as code")
    artifact.chmod(0o600)
    manifest = {
        "schema_version": 1,
        "adapter_id": plan["platform"] + "-lifecycle-v1",
        "version": "1.0.0",
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "release_sha256": "a" * 64,
        "contracts": CONTRACTS,
        "capabilities": [{k: plan[k] for k in ("operation", "tuple_sha256", "route_sha256")}],
        "constraint_sha256": "b" * 64,
        "not_before": 90,
        "expires_at": 200,
        "retest_triggers": sorted(TRIGGERS),
        "owner_role": "synthetic-owner",
        "implementation_sha256": implementation_digest(),
    }
    envelope = {
        "manifest": manifest,
        "key_id": "test",
        "signature": base64.b64encode(key.sign(signing_bytes(manifest))).decode(),
    }
    trust = {
        "schema_version": 1,
        "epoch": str(uuid4()),
        "expires_at": 200,
        "revoked_artifacts": [],
        "keys": [
            {
                "id": "test",
                "public_key": base64.b64encode(key.public_key().public_bytes_raw()).decode(),
                "not_before": 90,
                "expires_at": 200,
                "revoked": False,
                "adapters": [manifest["adapter_id"]],
            }
        ],
    }
    return (
        ExtensionTrust(write(tmp_path / "trust.json", trust), lambda: 100),
        write(tmp_path / "envelope.json", envelope),
        artifact,
        manifest,
        trust,
    )


@pytest.mark.parametrize("platform", ["vmware", "ahv"])
@pytest.mark.parametrize("op", ["power_on", "shutdown", "power_off", "resize_cpu", "resize_memory"])
def test_native_request_is_exact_and_preserves_unowned_fields(platform: str, op: str) -> None:
    b = binding()
    p, before = plan_for(b, platform, op)
    b = replace(b, operation_plan_sha256=digest(p))
    validate(p, b)
    req = request(p, before, '"etag-3"', b.operation_id)
    assert req["path"].startswith("/api/") and p["object_id"] in req["path"]
    if platform == "ahv":
        assert req["headers"] == {"If-Match": '"etag-3"', "Ntnx-Request-Id": b.operation_id}
        if op.startswith("resize_"):
            assert req["body"]["nics"] == before["nics"]
            assert achieved(p, req["body"])
    elif op == "resize_memory":
        assert req["body"] == {"size_MiB": 4096}
    with pytest.raises(NativeHeld, match="baseline_drift"):
        request(p, before | {"drift": 1}, '"etag-3"', b.operation_id)


@pytest.mark.parametrize(
    "mutation",
    ["signature", "artifact", "revoked", "expired", "contract", "implementation", "scope"],
)
def test_signed_admission_denies_changed_untrusted_or_incompatible_package(
    tmp_path: Path, mutation: str
) -> None:
    p, _ = plan_for(binding())
    trust, envelope_path, artifact, manifest, config = signed(tmp_path, p)
    cap = {k: p[k] for k in ("operation", "tuple_sha256", "route_sha256")}
    expected = digest(manifest)
    assert trust.admit(envelope_path, artifact, expected, cap) == manifest
    envelope = json.loads(envelope_path.read_text())
    if mutation == "signature":
        envelope["signature"] = base64.b64encode(bytes(64)).decode()
    elif mutation == "artifact":
        artifact.write_bytes(b"tampered")
    elif mutation == "revoked":
        config["keys"][0]["revoked"] = True
    elif mutation == "expired":
        config["expires_at"] = 100
    elif mutation == "scope":
        cap = cap | {"route_sha256": "0" * 64}
    else:
        envelope["manifest"]["contracts" if mutation == "contract" else "implementation_sha256"] = (
            {} if mutation == "contract" else "0" * 64
        )
        expected = digest(envelope["manifest"])
    write(trust.trust_file, config)
    write(envelope_path, envelope)
    with pytest.raises(NativeHeld):
        trust.admit(envelope_path, artifact, expected, cap)


class Journal:
    def __init__(self) -> None:
        self.claimed = False
        self.events: list[tuple[str, dict[str, Any]]] = []

    def claim(self, b: NativeBinding) -> bool:
        if self.claimed:
            return False
        self.claimed = True
        return True

    def record(self, b: NativeBinding, event: str, facts: dict[str, Any]) -> None:
        self.events.append((event, facts))

    def resources(self, b: NativeBinding) -> dict[str, dict[str, str]]:
        return {
            f["resource_key"]: {"kind": f["kind"], "id": f["native_id"]}
            for e, f in self.events
            if e == "request_accepted"
        }

    def transfers(self, b: NativeBinding) -> dict[str, dict[str, Any]]:
        return {}


class Transport:
    def __init__(self, current: dict[str, Any]) -> None:
        self.current = current
        self.sent = 0
        self.lose = False
        self.before_send: Callable[[], None] = lambda: None

    def read(self, platform: str, object_id: str) -> tuple[dict[str, Any], str]:
        return self.current, '"etag-3"'

    def send(
        self, platform: str, document: dict[str, Any], boundary: Callable[[], None]
    ) -> dict[str, Any]:
        self.before_send()
        boundary()
        self.sent += 1
        self.current["power_state"] = "POWERED_ON"
        if self.lose:
            raise NativeHeld("response_lost")
        return {"document": {}, "status": 204, "etag": ""}


class Authority:
    def require_current(self, b: NativeBinding, boundary: str) -> None:
        pass


def test_response_loss_never_resubmits_and_independent_readback_recovers(tmp_path: Path) -> None:
    b = binding()
    p, current = plan_for(b)
    trust, envelope, artifact, manifest, _ = signed(tmp_path, p)
    p["adapter_sha256"] = digest(manifest)
    b = replace(b, operation_plan_sha256=digest(p))
    path = write(tmp_path / "plan.json", p)
    journal, transport = Journal(), Transport(current)
    adapter = PlatformApi(path, envelope, artifact, trust, transport, journal)
    # Separate synthetic observer transports share only the simulated native state.
    observer = PlatformObserver(path, Transport(current), lambda: 100)
    executor = NativeApiExecution(Authority(), journal, adapter, observer, lambda: 100)
    transport.lose = True
    with pytest.raises(NativeHeld, match="requires_reconciliation"):
        executor.execute(b)
    assert executor.reconcile(b)["outcome"] == "observed_present"
    with pytest.raises(NativeHeld, match="requires_reconciliation"):
        executor.execute(b)
    assert transport.sent == 1


def test_revocation_between_prepare_and_send_blocks_native_request(tmp_path: Path) -> None:
    b = binding()
    p, current = plan_for(b)
    trust, envelope, artifact, manifest, config = signed(tmp_path, p)
    p["adapter_sha256"] = digest(manifest)
    b = replace(b, operation_plan_sha256=digest(p))
    path = write(tmp_path / "plan.json", p)
    journal, transport = Journal(), Transport(current)
    adapter = PlatformApi(path, envelope, artifact, trust, transport, journal)

    def revoke() -> None:
        config["revoked_artifacts"] = [manifest["artifact_sha256"]]
        write(trust.trust_file, config)

    transport.before_send = revoke
    with pytest.raises(NativeHeld, match="revoked"):
        adapter.execute(b, lambda: None)
    assert transport.sent == 0


def test_upgrade_requires_exact_transition_common_path_and_recovery_evidence(
    tmp_path: Path,
) -> None:
    p, _ = plan_for(binding())
    _, _, _, previous, _ = signed(tmp_path, p)
    candidate = previous | {"version": "1.1.0"}
    proof = {
        "from_sha256": digest(previous),
        "to_sha256": digest(candidate),
        "active_attempts": [],
        "unknown_attempts": [],
        "common_paths_sha256": "a" * 64,
        "recovery_sha256": "b" * 64,
        "decision": "accepted",
        "expires_at": 200,
    }
    upgrade(previous, candidate, proof, 100)
    for change in (
        {"unknown_attempts": ["uncertain"]},
        {"active_attempts": ["busy"]},
        {"expires_at": 100},
        {"to_sha256": "0" * 64},
        {"decision": "pending"},
    ):
        with pytest.raises(NativeHeld, match="transition_held"):
            upgrade(previous, candidate, proof | change, 100)
