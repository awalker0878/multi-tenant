"""Fixed, authenticated owner protocols for commissioned guest/service/data integrations.

An owner protocol is a concrete integration endpoint, not a shell command or an
assertion that an application-specific protocol has been implemented. The peer must
enforce the exact immutable operation, custody generation and single-writer fence.
"""

import hashlib
import http.client
import json
import re
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
    identity,
    sha256,
)
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, PinnedConnection


class OwnerProtocolClient:
    def __init__(self, endpoint: NativeEndpoint, *, read_only: bool = False) -> None:
        self.endpoint, self.read_only = endpoint, read_only

    def credential(self) -> str:
        token = protected_read(self.endpoint.token_file, 4096).decode("ascii").rstrip("\r\n")
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,4096}", token):
            raise NativeHeld("invalid_migration_protocol_credential")
        return token

    def call(self, path: str, body: dict[str, Any], current: Callable[[], None]) -> dict[str, Any]:
        if path not in {
            "/v1/migration/effects",
            "/v1/migration/observations",
            "/v1/native/effects",
            "/v1/native/observations",
        }:
            raise NativeHeld("migration_protocol_route_denied")
        if self.read_only and not path.endswith("/observations"):
            raise NativeHeld("observer_effect_denied")
        token = self.credential()
        fingerprint = hashlib.sha256(token.encode()).hexdigest()

        def recheck() -> None:
            current()
            if hashlib.sha256(self.credential().encode()).hexdigest() != fingerprint:
                raise NativeHeld("owner_protocol_credential_changed")

        raw = json.dumps(body, allow_nan=False, separators=(",", ":")).encode()
        if len(raw) > 131072:
            raise NativeHeld("migration_protocol_request_bound")
        connection = PinnedConnection(self.endpoint)
        try:
            recheck()
            connection.request(
                "POST",
                urlsplit(self.endpoint.base_url).path.rstrip("/") + path,
                raw,
                {
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                    "Idempotency-Key": digest(body),
                },
            )
            response = connection.getresponse()
            if (
                response.status != 200
                or response.getheader("Content-Encoding", "identity") != "identity"
                or response.getheader("Content-Type", "").split(";")[0] != "application/json"
            ):
                raise NativeHeld("migration_protocol_unconfirmed")
            data = bytearray()
            deadline = time.monotonic() + 10
            while True:
                recheck()
                if time.monotonic() >= deadline:
                    raise NativeHeld("migration_protocol_deadline")
                chunk = response.read1(min(16384, 131073 - len(data)))
                data.extend(chunk)
                if len(data) > 131072:
                    raise NativeHeld("migration_protocol_response_bound")
                if not chunk:
                    recheck()
                    return decode(bytes(data), 131072)
        except (OSError, http.client.HTTPException):
            raise NativeHeld("migration_protocol_outcome_unknown") from None
        finally:
            connection.close()


class OwnerProtocolEffect:
    def __init__(
        self, plan: dict[str, Any], client: OwnerProtocolClient, journal: NativeJournal
    ) -> None:
        self.plan, self.client, self.journal = plan, client, journal

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        from lifecycle_worker.application.migration_runtime import MIGRATION_STAGES

        native_stages = {
            "reserve",
            "configure_guest",
            "enroll_services",
            "activate",
            "retire",
            "release",
        }
        stages = (
            native_stages
            if self.plan.get("kind") == "native_owner_protocol"
            else MIGRATION_STAGES - {"capture", "export_copy", "convert_copy", "import_target"}
        )
        if (
            set(self.plan) != {"schema_version", "kind", "stage", "protocol_sha256", "parameters"}
            or type(self.plan["schema_version"]) is not int
            or self.plan["schema_version"] != 1
            or self.plan["kind"] not in {"migration_owner_protocol", "native_owner_protocol"}
            or self.plan["stage"] not in stages
            or not sha256(self.plan["protocol_sha256"])
            or not isinstance(self.plan["parameters"], dict)
            or digest(self.plan) != binding.operation_plan_sha256
        ):
            raise NativeHeld("migration_protocol_plan_changed")
        return {"operation_plan_sha256": digest(self.plan), "native_write_authorized": False}

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        self.inspect(binding)
        self.journal.record(
            binding,
            "request_started",
            {"kind": "owner_protocol", "protocol_sha256": self.plan["protocol_sha256"]},
        )
        result = self.client.call(
            "/v1/native/effects"
            if self.plan["kind"] == "native_owner_protocol"
            else "/v1/migration/effects",
            {"schema_version": 1, "binding": binding.document(), "intent": self.plan},
            boundary,
        )
        if (
            set(result)
            != {
                "binding_sha256",
                "intent_sha256",
                "receipt_sha256",
                "submitted",
                "retry_authorized",
            }
            or result["binding_sha256"] != binding.fingerprint
            or result["intent_sha256"] != binding.operation_plan_sha256
            or not sha256(result["receipt_sha256"])
            or result["submitted"] is not True
            or result["retry_authorized"] is not False
        ):
            raise NativeHeld("migration_protocol_receipt_changed")
        self.journal.record(binding, "poll_observed", {"kind": "owner_protocol", **result})


class OwnerProtocolObserver:
    def __init__(
        self,
        client: OwnerProtocolClient,
        observer_id: str,
        writer_id: str,
        clock: Callable[[], int],
        *,
        family: str = "migration",
        identity_check: Callable[[], None] = lambda: None,
    ) -> None:
        self.observer_id, self.writer_id = identity(observer_id), identity(writer_id)
        if observer_id == writer_id:
            raise NativeHeld("independent_native_identity_required")
        if family not in {"native", "migration"}:
            raise NativeHeld("invalid_owner_protocol_family")
        self.family, self.identity_check = family, identity_check
        self.client, self.clock = client, clock

    def observe(self, binding: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]:
        # Reads remain available after a pause or expiry; they cannot authorize effects.
        result = self.client.call(
            "/v1/" + self.family + "/observations",
            {"schema_version": 1, "binding": binding.document(), "objects": objects},
            self.identity_check,
        )
        if (
            set(result)
            != {
                "binding_sha256",
                "intent_sha256",
                "observer_id",
                "independent",
                "outcome",
                "observed_at",
                "evidence_sha256",
            }
            or result.get("binding_sha256") != binding.fingerprint
            or result.get("observer_id") != self.observer_id
            or result.get("intent_sha256") != binding.operation_plan_sha256
            or result.get("independent") is not True
            or result.get("outcome") not in {"observed_present", "held"}
            or type(result.get("observed_at")) is not int
            or not 0 <= self.clock() - result["observed_at"] <= 5
            or not sha256(result.get("evidence_sha256"))
        ):
            raise NativeHeld("migration_protocol_observation_changed")
        return result
