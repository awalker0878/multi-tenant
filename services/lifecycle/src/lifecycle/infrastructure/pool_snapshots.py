"""Commissioned independent owner observations; fetching never renews measured timestamps."""

import hmac
import json
import os
import time
from pathlib import Path
from typing import Any

from lifecycle.application.reservations import Held
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import decode
from lifecycle.infrastructure.campaign_observers import protected
from lifecycle.infrastructure.native_effects import NativeEffectConnection, credential
from lifecycle.infrastructure.native_owners import endpoint


class NativePoolSnapshots:
    def __init__(self, configuration: Path) -> None:
        self.configuration = configuration

    def read(
        self, request: dict[str, Any], operation: str, reservation_id: str | None = None
    ) -> dict[str, Any]:
        raw = protected(str(self.configuration), 2097152)
        config = decode(raw)
        if (
            config["schema_version"] != 1
            or config["expires_at"] <= int(time.time())
            or config["reader_principal"] == config["writer_principal"]
            or not config["reader_principal"]
            or digest(request) not in config["approved_requests"]
        ):
            raise Held("pool_owner_not_commissioned")
        connection = NativeEffectConnection(endpoint(config["endpoint"]))
        try:
            connection.request(
                "POST",
                "/v1/native-pool-observations",
                json.dumps({
                    "operation": operation, "request": request, "reservation_id": reservation_id,
                }),
                {
                    "Authorization": "Bearer " + credential(endpoint(config["endpoint"]).credential_file),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            chunks = bytearray()
            deadline = time.monotonic() + 5
            while True:
                if time.monotonic() >= deadline:
                    raise Held("pool_native_observation_timeout")
                part = response.read1(min(65536, 2097153 - len(chunks)))
                if not part:
                    break
                chunks.extend(part)
                if len(chunks) > 2097152:
                    raise Held("pool_native_observation_bound")
            result = decode(bytes(chunks))
            if (
                response.status != 200
                or response.getheader("Content-Encoding", "identity") != "identity"
                or response.getheader("Content-Type", "").split(";")[0] != "application/json"
                or result["reader_principal"] != config["reader_principal"]
                or result["request_digest"] != digest(request)
                or protected(str(self.configuration), 2097152) != raw
            ):
                raise Held("pool_native_observation_unavailable")
            return result
        finally:
            connection.close()

    def pools(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        result = self.read(request, "pools")
        pools: list[dict[str, Any]] = result["pools"]
        if not 1 <= len(pools) <= 128 or len({p["id"] for p in pools}) != len(pools):
            raise Held("pool_native_observation_ambiguous")
        return pools

    def allocation(self, request: dict[str, Any], reservation_id: str) -> dict[str, Any]:
        return self.read(request, "allocation", reservation_id)


def capacity_caller(token: str) -> None:
    expected = protected(os.environ["LIFECYCLE_CAPACITY_CREDENTIAL_FILE"], 4096).decode().strip()
    config = decode(protected(os.environ["LIFECYCLE_POOL_OWNERS_FILE"], 2097152))
    outgoing = credential(endpoint(config["endpoint"]).credential_file)
    if expected == outgoing or not hmac.compare_digest(token, expected):
        raise Held("placement_caller_denied")
