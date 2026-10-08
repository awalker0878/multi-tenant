"""P07 native API effect boundary. Native admission remains owned by Lifecycle.

An adapter result is infrastructure evidence, never application readiness. A claimed
native mutation cannot run twice. Explicit immutable-transfer continuation retains
the original claim, authority, file lock and deadline.
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
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


def native_project_identity(value: Any) -> str:
    if isinstance(value, str) and re.fullmatch(r"datacenter-[1-9][0-9]{0,18}", value):
        return value
    return native_identity(value)


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
    operation_plan_sha256: str
    ownership_digest: str
    custody_id: str
    custody_generation: int
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
            "custody_id",
        ):
            identity(value[name])
        native_project_identity(value["project_id"])
        if (
            not all(
                sha256(value[key])
                for key in ("plan_digest", "operation_plan_sha256", "ownership_digest")
            )
            or type(value["custody_generation"]) is not int
            or not 0 <= value["custody_generation"] < 2**63
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


class NativeAuthority(Protocol):
    def require_current(self, binding: NativeBinding, boundary: str) -> None: ...


class NativeJournal(Protocol):
    def claim(self, binding: NativeBinding) -> bool: ...
    def record(self, binding: NativeBinding, event: str, facts: dict[str, Any]) -> None: ...
    def resources(self, binding: NativeBinding) -> dict[str, dict[str, str]]: ...
    def transfers(self, binding: NativeBinding) -> dict[str, dict[str, Any]]: ...


class NativeApiAdapter(Protocol):
    def inspect(self, binding: NativeBinding) -> dict[str, Any]: ...
    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None: ...


class NativeObserver(Protocol):
    def observe(self, binding: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class NativeTransferContinuation(Protocol):
    def resume_transfer(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        """Resume immutable reads only, excluding concurrent spool writers."""
        ...


class NativeApiExecution:
    def __init__(
        self,
        authority: NativeAuthority,
        journal: NativeJournal,
        adapter: NativeApiAdapter,
        observer: NativeObserver,
        clock: Callable[[], int],
    ) -> None:
        self.authority, self.journal, self.adapter = authority, journal, adapter
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
        inspection = self.adapter.inspect(binding)
        if not self.journal.claim(binding):
            raise NativeHeld("native_attempt_requires_reconciliation")
        self.journal.record(binding, "prepared", inspection)
        try:
            self.require_current(binding, "before_api_sequence")
            self.adapter.execute(
                binding, lambda: self.require_current(binding, "during_api_sequence")
            )
        except Exception:
            # Reads can recover accepted IDs after lost polling responses. They
            # cannot replay writes, renew authority or clear the unknown outcome.
            self.reconcile(binding)
            self.journal.record(
                binding, "outcome_unknown", {"reason": "native_request_or_authority_held"}
            )
            raise NativeHeld("native_attempt_requires_reconciliation") from None
        return {
            "binding_sha256": binding.fingerprint,
            "observation": self.reconcile(binding),
            "retry_authorized": False,
            "activation_authorized": False,
            "application_ready": False,
        }

    def continue_transfer(self, binding: NativeBinding) -> dict[str, Any]:
        NativeBinding.parse(binding.document())
        self.require_current(binding, "during_api_sequence")
        self.journal.resources(binding)
        if not isinstance(self.adapter, NativeTransferContinuation):
            raise NativeHeld("native_transfer_continuation_not_supported")
        self.adapter.inspect(binding)
        try:
            self.adapter.resume_transfer(
                binding, lambda: self.require_current(binding, "during_api_sequence")
            )
        except Exception:
            self.journal.record(
                binding, "continuation_held", {"reason": "immutable_transfer_not_confirmed"}
            )
            raise NativeHeld("native_transfer_continuation_held") from None
        return {
            "binding_sha256": binding.fingerprint,
            "observation": self.reconcile(binding),
            "retry_authorized": False,
            "activation_authorized": False,
            "application_ready": False,
        }

    def reconcile(self, binding: NativeBinding) -> dict[str, Any]:
        try:
            observation = self.observer.observe(binding, self.journal.resources(binding))
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
