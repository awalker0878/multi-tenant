"""Bounded bootstrap probes; no HTTP endpoint or dependency checks exist yet."""

from enum import StrEnum


class Probe(StrEnum):
    LIVENESS = "liveness"
    READINESS = "readiness"


def probe(mode: Probe) -> tuple[int, dict[str, str | bool]]:
    result: dict[str, str | bool] = {
        "service": "lifecycle",
        "component": "lifecycle-workers",
        "component_kind": "worker_bootstrap",
        "task_consumption_enabled": False,
        "probe": mode.value,
        "scope": "process_bootstrap",
        "native_operations_enabled": False,
    }
    if mode is Probe.LIVENESS:
        result["status"] = "ok"
        return 0, result

    result["status"] = "not_ready"
    result["reason"] = "worker_dependencies_not_implemented"
    return 1, result
