"""Lifecycle's single-use stage grant bound to the exact native API invocation."""

import json
from collections.abc import Callable
from typing import Any, Protocol

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest, identity, sha256


class NativeBoundaryClient(Protocol):
    def check(self, stage_grant: dict[str, Any], boundary: str) -> dict[str, Any]: ...


class GrantedNativeAuthority:
    def __init__(
        self, grant: dict[str, Any], client: NativeBoundaryClient, clock: Callable[[], int]
    ) -> None:
        self.grant = json.loads(json.dumps(grant, allow_nan=False))
        migration = (
            self.grant.get("schema_version") == 2 and type(self.grant.get("schema_version")) is int
        )
        if set(self.grant) != {
            "job_id",
            "operation_id",
            "attempt_id",
            "grant_id",
            "stage",
            "plan_sha256",
            "intent_digest",
            "epoch",
            "executor_id",
            "expires_at",
            "native_binding",
        } | ({"schema_version"} if migration else set()) or (
            not migration and self.grant["stage"] != "provision"
        ):
            raise NativeHeld("invalid_native_stage_grant")
        self.binding = NativeBinding.parse(self.grant["native_binding"])
        if migration:
            from lifecycle_worker.application.migration_runtime import MIGRATION_STAGES

            if (
                self.grant["stage"] not in MIGRATION_STAGES
                or self.grant["intent_digest"] != self.binding.operation_plan_sha256
            ):
                raise NativeHeld("migration_stage_intent_mismatch")
        for key in ("job_id", "operation_id", "attempt_id", "epoch", "executor_id", "expires_at"):
            if digest(self.grant[key]) != digest(self.binding.document()[key]):
                raise NativeHeld("native_stage_binding_mismatch")
        identity(self.grant["grant_id"])
        if not sha256(self.grant["plan_sha256"]) or not sha256(self.grant["intent_digest"]):
            raise NativeHeld("invalid_native_stage_grant")
        self.client, self.clock = client, clock

    def require_current(self, binding: NativeBinding, boundary: str) -> None:
        NativeBinding.parse(binding.document())
        if digest(binding.document()) != digest(self.binding.document()) or boundary not in {
            "preflight",
            "before_api_sequence",
            "during_api_sequence",
        }:
            raise NativeHeld("native_stage_binding_mismatch")
        if binding.expires_at <= self.clock():
            raise NativeHeld("native_authority_expired")
        try:
            reply = self.client.check(self.grant, boundary)
            expected = {
                "binding_sha256": digest(self.grant),
                "epoch": binding.epoch,
                "boundary": boundary,
                "allowed": True,
                "authority_use": "native_boundary",
                "expires_at": binding.expires_at,
            }
            if set(reply) != set(expected) | {"evaluated_at"} or any(
                digest(reply.get(k)) != digest(v) for k, v in expected.items()
            ):
                raise NativeHeld("native_authority_denied")
            if (
                type(reply["evaluated_at"]) is not int
                or not 0 <= self.clock() - reply["evaluated_at"] <= 5
                or binding.expires_at <= self.clock()
            ):
                raise NativeHeld("native_authority_expired")
        except NativeHeld:
            raise
        except Exception:
            # A lost redemption response may follow durable consumption. Never retry it.
            raise NativeHeld("native_authority_unavailable") from None
