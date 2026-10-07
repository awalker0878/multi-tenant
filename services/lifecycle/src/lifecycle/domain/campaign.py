"""Migration schedules and measured stage admission; these rules grant no native authority."""

import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from lifecycle.domain.execution import Rejected, identity
from lifecycle.domain.native_workflow import checksum, exact, integer

PHASES = ("capture", "transfer", "conversion", "import", "validation", "cutover")
BYTE_PHASES = frozenset({"transfer", "conversion", "import"})
STAGE_PHASE = {
    "source_prepare": "capture",
    "capture": "capture",
    "restart_baseline_source": "capture",
    "export_copy": "transfer",
    "convert_copy": "conversion",
    "import_target": "import",
    "transform_copy": "validation",
    "rehearsal_validate": "validation",
    "retain_rehearsal": "validation",
    "fence_source": "cutover",
    "final_sync": "cutover",
    "shutdown_source": "cutover",
    "validate_target": "cutover",
    "admit_writes": "cutover",
    "verify_activation": "cutover",
}


def bounded(value: Any, low: int, high: int) -> int:
    result = integer(value, low)
    if result > high:
        raise Rejected("campaign_value_bound", 422)
    return result


def label(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value.strip()) <= 120
        or any(ord(c) < 32 for c in value)
    ):
        raise Rejected("invalid_campaign_label", 422)
    return value


def intervals(value: Any, maximum: int = 128) -> list[dict[str, int]]:
    if not isinstance(value, list) or len(value) > maximum:
        raise Rejected("campaign_interval_bound", 422)
    result = []
    for item in value:
        exact(item, {"start", "end"})
        start, end = integer(item["start"]), integer(item["end"], 1)
        if not start < end <= 253402300799:
            raise Rejected("invalid_campaign_interval", 422)
        result.append({"start": start, "end": end})
    result.sort(key=lambda item: item["start"])
    if any(a["end"] > b["start"] for a, b in zip(result, result[1:], strict=False)):
        raise Rejected("overlapping_campaign_intervals", 422)
    return result


def schedule(value: Any) -> dict[str, Any]:
    exact(
        value,
        {
            "name",
            "timezone",
            "windows",
            "cutover_windows",
            "blackouts",
            "stagger_seconds",
            "max_active",
            "phase_limits",
            "failure_limit",
        },
    )
    label(value["name"])
    if not isinstance(value["timezone"], str) or len(value["timezone"]) > 100:
        raise Rejected("invalid_campaign_timezone", 422)
    try:
        ZoneInfo(value["timezone"])
    except (ZoneInfoNotFoundError, ValueError):
        raise Rejected("invalid_campaign_timezone", 422) from None
    windows = intervals(value["windows"])
    cutover = intervals(value["cutover_windows"])
    if not windows or not cutover:
        raise Rejected("explicit_migration_windows_required", 422)
    limits = exact(value["phase_limits"], set(PHASES))
    for limit in limits.values():
        bounded(limit, 1, 1000)
    bounded(value["max_active"], 1, 1000)
    bounded(value["failure_limit"], 1, 1000)
    bounded(value["stagger_seconds"], 0, 86400)
    return dict(value) | {
        "windows": windows,
        "cutover_windows": cutover,
        "blackouts": intervals(value["blackouts"]),
    }


def next_window(
    settings: dict[str, Any], now: int, seconds: int, cutover: bool = False
) -> int | None:
    """Find a complete UTC interval, including blackout splitting, without sleeping."""
    integer(now)
    integer(seconds, 1)
    key = "cutover_windows" if cutover else "windows"
    for window in settings[key]:
        start = max(now, window["start"])
        for blackout in settings["blackouts"]:
            if blackout["end"] <= start or blackout["start"] >= window["end"]:
                continue
            if start + seconds <= blackout["start"]:
                break
            start = max(start, blackout["end"])
        if start + seconds <= window["end"]:
            return int(start)
    return None


def dependency_order(members: Any) -> list[str]:
    if not isinstance(members, list) or not 1 <= len(members) <= 1000:
        raise Rejected("campaign_member_bound", 422)
    graph: dict[str, set[str]] = {}
    for member in members:
        key = identity(member["id"])
        if key in graph:
            raise Rejected("duplicate_campaign_member", 422)
        deps = member["depends_on"]
        if not isinstance(deps, list) or len(deps) > 1000:
            raise Rejected("invalid_campaign_dependencies", 422)
        dep_set = {identity(d) for d in deps}
        if len(dep_set) != len(deps) or key in dep_set:
            raise Rejected("invalid_campaign_dependencies", 422)
        graph[key] = dep_set
    if any(deps - graph.keys() for deps in graph.values()):
        raise Rejected("unknown_campaign_dependency", 422)
    result: list[str] = []
    while graph:
        ready = sorted(key for key, deps in graph.items() if not deps)
        if not ready:
            raise Rejected("campaign_dependency_cycle", 422)
        result.extend(ready)
        for key in ready:
            del graph[key]
        for deps in graph.values():
            deps.difference_update(ready)
    return result


def performance_sample(value: Any, now: int) -> dict[str, Any]:
    """Only authenticated workers can publish a sample; browser input is not measurement."""
    exact(
        value,
        {
            "route_sha256",
            "phase",
            "bytes",
            "elapsed_ms",
            "concurrency",
            "observed_at",
            "expires_at",
            "evidence_sha256",
            "production_impact_ok",
        },
    )
    checksum(value["route_sha256"])
    checksum(value["evidence_sha256"])
    if value["phase"] not in PHASES or type(value["production_impact_ok"]) is not bool:
        raise Rejected("invalid_performance_sample", 422)
    bounded(value["bytes"], 0, 2**60)
    bounded(value["elapsed_ms"], 1, 7 * 86400 * 1000)
    bounded(value["concurrency"], 1, 1000)
    if (
        not 0 <= now - integer(value["observed_at"]) <= 86400
        or not now < integer(value["expires_at"]) <= value["observed_at"] + 7 * 86400
    ):
        raise Rejected("performance_sample_stale", 423)
    if value["phase"] in BYTE_PHASES and not value["bytes"]:
        raise Rejected("performance_bytes_required", 422)
    return dict(value)


def phase_estimate(
    samples: list[dict[str, Any]], phase: str, amount: int
) -> tuple[int | None, str | None]:
    latest = max((s["observed_at"] for s in samples), default=-1)
    if any(not s["production_impact_ok"] for s in samples if s["observed_at"] == latest):
        return None, "production_impact_exceeded_" + phase
    current = [s for s in samples if s["production_impact_ok"]]
    if not current:
        return None, "measurement_required_" + phase
    if phase in BYTE_PHASES:
        # Integer arithmetic also avoids losing byte precision on very large disks.
        duration_ms = max(
            (amount * s["elapsed_ms"] + s["bytes"] - 1) // s["bytes"] for s in current
        )
    else:
        duration_ms = max(s["elapsed_ms"] for s in current)
    return max(1, (duration_ms * 5 + 3999) // 4000), None


def comparable(
    samples: list[dict[str, Any]], route: str, now: int
) -> dict[tuple[str, int], list[dict[str, Any]]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for sample in samples:
        if sample["route_sha256"] == route and sample["observed_at"] <= now < sample["expires_at"]:
            grouped.setdefault((sample["phase"], sample["concurrency"]), []).append(sample)
    return grouped


def estimate(
    samples: list[dict[str, Any]], route: str, sizes: dict[str, int], now: int, concurrency: int = 1
) -> dict[str, Any]:
    """Slowest current comparable observation plus 25%; never extrapolate concurrency."""
    checksum(route)
    bounded(concurrency, 1, 1000)
    exact(sizes, set(PHASES))
    grouped = comparable(samples, route, now)
    phases: dict[str, int | None] = {}
    holds = []
    for phase in PHASES:
        duration, reason = phase_estimate(
            grouped.get((phase, concurrency), []), phase, integer(sizes[phase])
        )
        phases[phase] = duration
        if reason:
            holds.append(reason)
    return {
        "phases": phases,
        "total_seconds": None if holds else sum(v or 0 for v in phases.values()),
        "holds": holds,
        "margin_percent": 25,
        "concurrency": concurrency,
    }


def campaign_estimate(
    samples: list[dict[str, Any]], spec: dict[str, Any], settings: dict[str, Any], now: int
) -> dict[str, Any]:
    """Bound each phase at every allowed occupancy; a limit alone is not a benchmark."""
    from lifecycle.domain.migration import stages

    required = {STAGE_PHASE[s] for s in stages(spec)}
    grouped = comparable(samples, spec["route_sha256"], now)
    phases: dict[str, int | None] = {}
    holds = []
    for phase in PHASES:
        if phase not in required:
            phases[phase] = 0
            continue
        values, reasons = [], []
        for occupancy in range(1, min(settings["max_active"], settings["phase_limits"][phase]) + 1):
            duration, reason = phase_estimate(
                grouped.get((phase, occupancy), []), phase, spec["sizes"][phase]
            )
            if reason:
                reasons.append(f"{reason}_concurrency_{occupancy}")
            if duration is not None:
                values.append(duration)
        if reasons:
            holds.append(reasons[0])
        phases[phase] = None if reasons else max(values)
    cold = spec["method"] == "VM_COLD_EXPORT"
    # Capture also interrupts a warm source. A qualified restart/delta is still required.
    outage = list(phases.values()) if cold else [phases["capture"], phases["cutover"]]
    return {
        "phases": phases,
        "total_seconds": None if holds else sum(v or 0 for v in phases.values()),
        "outage_seconds": None if any(v is None for v in outage) else sum(v or 0 for v in outage),
        "holds": holds,
        "margin_percent": 25,
        "phase_limits": settings["phase_limits"],
    }


def resource_demands(value: Any) -> dict[str, int]:
    if not isinstance(value, dict) or not 1 <= len(value) <= 64:
        raise Rejected("campaign_resource_demands_required", 422)
    result = {}
    for key, amount in value.items():
        if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}:[a-f0-9]{64}", key):
            raise Rejected("invalid_campaign_pool", 422)
        result[key] = bounded(amount, 1, 2**60)
    return result


def capacity_holds(
    demands: dict[str, int], capacities: dict[str, int], used: dict[str, int]
) -> list[str]:
    return [
        key
        for key, amount in sorted(demands.items())
        if key not in capacities or amount + used.get(key, 0) > capacities[key]
    ]
