"""P07 saved-plan effect boundary. Native admission remains owned by Lifecycle.

An adapter result is infrastructure evidence, never application readiness. A claimed
attempt cannot run twice, even after an error, crash, lease expiry or missing readback.
"""

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from uuid import UUID


class NativeHeld(Exception):
    """Only fixed, value-free reason codes may cross the worker boundary."""


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def decode(raw: bytes, limit: int = 2_097_152) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    def constant(_: str) -> None:
        raise ValueError

    try:
        if len(raw) > limit:
            raise ValueError
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise NativeHeld("invalid_native_document") from None


def identity(value: Any) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
        return value
    except ValueError:
        raise NativeHeld("invalid_native_identity") from None


def native_identity(value: Any) -> str:
    if isinstance(value, str) and re.fullmatch(r"[a-f0-9]{32}", value):
        return value
    return identity(value)


def sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


@dataclass(frozen=True)
class NativeBinding:
    tenant_id: str
    site_id: str
    project_id: str
    resource_id: str
    job_id: str
    operation_id: str
    attempt_id: str
    campaign_id: str
    executor_id: str
    epoch: str
    plan_digest: str
    bundle_sha256: str
    workspace: str
    state_lineage: str
    state_serial: int
    expires_at: int

    @classmethod
    def parse(cls, value: dict[str, Any]) -> "NativeBinding":
        if set(value) != set(cls.__dataclass_fields__):
            raise NativeHeld("invalid_native_binding")
        for name in (
            "tenant_id",
            "site_id",
            "resource_id",
            "job_id",
            "operation_id",
            "attempt_id",
            "campaign_id",
            "executor_id",
            "epoch",
            "state_lineage",
        ):
            identity(value[name])
        native_identity(value["project_id"])
        if (
            not all(sha256(value[key]) for key in ("plan_digest", "bundle_sha256"))
            or not isinstance(value["workspace"], str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value["workspace"]) is None
            or type(value["state_serial"]) is not int
            or not 0 <= value["state_serial"] < 2**63
            or type(value["expires_at"]) is not int
            or value["expires_at"] <= 0
        ):
            raise NativeHeld("invalid_native_binding")
        return cls(**value)

    def document(self) -> dict[str, Any]:
        return dict(vars(self))

    @property
    def fingerprint(self) -> str:
        return digest(self.document())


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int | None
    interrupted: bool


class NativeAuthority(Protocol):
    def require_current(self, binding: NativeBinding, boundary: str) -> None:
        """Authenticate current owner authority, exact scope, epoch and stop/revocation state."""
        ...


class NativeJournal(Protocol):
    def claim(self, binding: NativeBinding) -> bool:
        """Durably claim once, excluding overlapping project/workspace writers."""
        ...

    def record(self, binding: NativeBinding, event: str, facts: dict[str, Any]) -> None: ...


class SavedPlanTool(Protocol):
    def inspect(self, binding: NativeBinding) -> dict[str, Any]: ...
    def apply(self, binding: NativeBinding, heartbeat: Callable[[], None]) -> ProcessResult: ...
    def state(self, binding: NativeBinding) -> dict[str, Any]: ...


class NativeObserver(Protocol):
    def observe(self, binding: NativeBinding, state: dict[str, Any]) -> dict[str, Any]: ...


class SavedPlanExecution:
    def __init__(
        self,
        authority: NativeAuthority,
        journal: NativeJournal,
        tool: SavedPlanTool,
        observer: NativeObserver,
        clock: Callable[[], int],
    ) -> None:
        self.authority, self.journal, self.tool = authority, journal, tool
        self.observer, self.clock = observer, clock

    def require_current(self, binding: NativeBinding, boundary: str) -> None:
        if binding.expires_at <= self.clock():
            raise NativeHeld("native_authority_expired")
        self.authority.require_current(binding, boundary)
        if binding.expires_at <= self.clock():
            raise NativeHeld("native_authority_expired")

    def execute(self, binding: NativeBinding) -> dict[str, Any]:
        NativeBinding.parse(binding.document())
        self.require_current(binding, "preflight")
        inspection = self.tool.inspect(binding)
        # Inspection is not an authority receipt. The claim is committed before an effect.
        if not self.journal.claim(binding):
            raise NativeHeld("native_attempt_requires_reconciliation")
        self.journal.record(binding, "prepared", inspection)
        try:
            self.require_current(binding, "before_saved_plan_apply")
            self.journal.record(binding, "apply_started", {})
            result = self.tool.apply(
                binding, lambda: self.require_current(binding, "during_saved_plan_apply")
            )
            self.journal.record(
                binding,
                "process_exited",
                {"exit_code": result.exit_code, "interrupted": result.interrupted},
            )
        except Exception:
            # An exception may follow provider acceptance. Never translate it into absence.
            self.journal.record(binding, "outcome_unknown", {"reason": "apply_or_authority_held"})
            raise NativeHeld("native_attempt_requires_reconciliation") from None
        observation = self.reconcile(binding)
        return {
            "binding_sha256": binding.fingerprint,
            "process_exit_code": result.exit_code,
            "interrupted": result.interrupted,
            "observation": observation,
            "retry_authorized": False,
            "activation_authorized": False,
            "application_ready": False,
        }

    def reconcile(self, binding: NativeBinding) -> dict[str, Any]:
        # Read-only observation is useful after write authority has expired or been revoked.
        # Its own authenticated observer scope must still be current.
        try:
            state = self.tool.state(binding)
            observation = self.observer.observe(binding, state)
            if (
                observation.get("binding_sha256") != binding.fingerprint
                or observation.get("independent") is not True
                or observation.get("outcome") not in {"observed_present", "held"}
                or type(observation.get("observed_at")) is not int
                or not 0 <= self.clock() - observation["observed_at"] <= 5
            ):
                raise NativeHeld("invalid_native_observation")
        except Exception:
            observation = {
                "binding_sha256": binding.fingerprint,
                "outcome": "held",
                "reason": "native_readback_unavailable",
                "observed_at": self.clock(),
                "independent": False,
            }
        self.journal.record(binding, "readback", observation)
        return observation


ResourceKind = Literal["server", "port", "volume"]
RESOURCE_TYPES: Mapping[str, ResourceKind] = {
    "openstack_compute_instance_v2": "server",
    "openstack_networking_port_v2": "port",
    "openstack_blockstorage_volume_v3": "volume",
}
