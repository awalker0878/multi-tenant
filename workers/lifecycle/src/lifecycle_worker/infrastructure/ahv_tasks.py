"""Prism task submission and reconciliation shared by source and destination roles."""

import re
import time
from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import quote
from uuid import UUID, uuid5

from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    digest,
    identity,
)
from lifecycle_worker.infrastructure.ahv_http import COLLECTIONS, AhvTransport, read


class AhvJournal(NativeJournal, Protocol):
    def ahv_tasks(self, binding: NativeBinding) -> dict[str, dict[str, Any]]: ...


def completed(api: AhvTransport, task: dict[str, Any], boundary: Callable[[], None]) -> str | None:
    task_id = task_identity(task.get("task_id"))
    data = read(api, "/api/prism/v4.3/config/tasks/" + quote(task_id, safe=":="), boundary)
    if data.get("extId") != task["task_id"]:
        raise NativeHeld("ahv_task_identity_changed")
    if data.get("status") in {"QUEUED", "RUNNING"}:
        return None
    if (
        data.get("status") != "SUCCEEDED"
        or data.get("errorMessages")
        or data.get("legacyErrorMessage")
        or data.get("warnings")
    ):
        raise NativeHeld("ahv_task_failed_or_unknown")
    entities = data.get("entitiesAffected")
    if not isinstance(entities, list) or len(entities) != 1:
        raise NativeHeld("ahv_task_object_ambiguous")
    return identity(entities[0].get("extId"))


def task_identity(value: Any) -> str:
    # Prism's task namespace is a base64 prefix, commonly ``ZXJnb24=`` (ergon).
    if (
        not isinstance(value, str)
        or len(value) > 160
        or re.fullmatch(r"[A-Za-z0-9/+]{1,120}={0,2}:[A-Fa-f0-9-]{36}", value) is None
    ):
        raise NativeHeld("ahv_task_identity_missing")
    identity(value.rsplit(":", 1)[1])
    return value


def submit(
    api: AhvTransport,
    journal: AhvJournal,
    b: NativeBinding,
    key: str,
    kind: str,
    body: dict[str, Any],
    current: Callable[[], None],
    interval: float = 1,
) -> str:
    request_id = str(uuid5(UUID(b.operation_id), key))
    current()
    journal.record(
        b,
        "request_started",
        {
            "resource_key": key,
            "kind": kind,
            "request_id": request_id,
            "payload_sha256": digest(body),
        },
    )
    reply = api.call("POST", COLLECTIONS[kind], body, {"Ntnx-Request-Id": request_id}, current)
    task_id = task_identity(reply["document"].get("data", {}).get("extId"))
    task = {"resource_key": key, "kind": kind, "task_id": task_id, "request_id": request_id}
    # Persist acceptance before the first poll. Interrupted POSTs are never retried.
    journal.record(b, "ahv_task_accepted", task)
    while True:
        current()
        native_id = completed(api, task, current)
        if native_id is not None:
            journal.record(
                b,
                "request_accepted",
                {
                    "resource_key": key,
                    "kind": kind,
                    "native_id": native_id,
                    "task_id": task_id,
                    "request_id": request_id,
                },
            )
            return native_id
        time.sleep(interval)
