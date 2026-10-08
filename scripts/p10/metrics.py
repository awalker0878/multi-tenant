"""Reproducible measurements: failures and unserved tenants remain in the denominator."""

from __future__ import annotations

import math

from evidence import number, require, sha256


def summarize(records, tenants, start_ns, end_ns, targets=None):
    number(start_ns)
    number(end_ns)
    require(
        end_ns > start_ns
        and isinstance(tenants, list)
        and tenants
        and len(set(tenants)) == len(tenants),
        "invalid_measurement_window",
    )
    require(
        isinstance(records, list) and 0 < len(records) <= 1000000,
        "empty_or_unbounded_samples",
    )
    counts = {t: 0 for t in tenants}
    attempts = {t: 0 for t in tenants}
    durations, seen = [], set()
    for row in records:
        require(
            set(row) == {"id", "tenant_id", "start_ns", "end_ns", "outcome"},
            "invalid_sample",
        )
        require(
            row["id"] not in seen and row["tenant_id"] in counts,
            "duplicate_or_unknown_sample",
        )
        seen.add(row["id"])
        begin, end = number(row["start_ns"]), number(row["end_ns"])
        require(start_ns <= begin <= end <= end_ns, "sample_outside_window")
        require(
            row["outcome"] in {"succeeded", "held", "failed", "unknown"},
            "invalid_outcome",
        )
        durations.append((end - begin) / 1000000)
        attempts[row["tenant_id"]] += 1
        counts[row["tenant_id"]] += int(row["outcome"] == "succeeded")
    durations.sort()
    percentile = lambda q: durations[max(0, math.ceil(q * len(durations)) - 1)]
    successes = sum(counts.values())
    total = len(records)
    squares = sum(n * n for n in counts.values())
    fairness = successes**2 / (len(tenants) * squares) if squares else 0
    result = {
        "samples": total,
        "succeeded": successes,
        "non_success": total - successes,
        "measurement_seconds": (end_ns - start_ns) / 1e9,
        "throughput_per_second": successes / ((end_ns - start_ns) / 1e9),
        "error_fraction": (total - successes) / total,
        "latency_ms": {
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
            "max": durations[-1],
        },
        "percentile_method": "nearest_rank_all_attempts_no_warmup_exclusion",
        "tenant_successes": counts,
        "tenant_attempts": attempts,
        "jain_fairness": fairness,
        "unserved_tenants": [t for t, n in counts.items() if n == 0],
        "slo_result": "NOT_EVALUATED",
        "capacity_claim": False,
    }
    if targets is not None:
        require(
            set(targets)
            == {
                "p95_ms",
                "maximum_error_fraction",
                "minimum_fairness",
                "minimum_samples",
                "approved_model_sha256",
            },
            "incomplete_targets",
        )
        require(
            sha256(targets["approved_model_sha256"]),
            "unbound_workload_model",
        )
        for key in (
            "p95_ms",
            "maximum_error_fraction",
            "minimum_fairness",
            "minimum_samples",
        ):
            number(targets[key])
        require(
            type(targets["minimum_samples"]) is int
            and targets["minimum_samples"] > 0
            and targets["maximum_error_fraction"] <= 1
            and targets["minimum_fairness"] <= 1,
            "invalid_targets",
        )
        passed = (
            result["latency_ms"]["p95"] <= targets["p95_ms"]
            and result["error_fraction"] <= targets["maximum_error_fraction"]
            and fairness >= targets["minimum_fairness"]
            and total >= targets["minimum_samples"]
            and not result["unserved_tenants"]
        )
        result.update(slo_result="PASSED" if passed else "FAILED", targets=targets)
    return result
