"""Measured restore objectives are evaluated per representative dataset profile."""

from typing import Any

from planning.domain.model import digest


def recovery_checks(
    intent: dict[str, Any], destination: dict[str, Any], profile: dict[str, Any],
    policy: dict[str, Any], data: dict[str, Any], now: int,
) -> list[tuple[str, str, str, bool]]:
    rows = data["recovery_measurements"]
    if len(rows) > 512:
        raise ValueError("recovery_measurement_bound")
    accepted = policy["recovery_profile"]
    checks = []
    for dataset in intent["datasets"]:
        objective = dataset["recovery"]
        mandatory = objective["strength"] == "required"
        samples = [m for m in rows if m.get("dataset_id") == dataset["id"]]
        status, reason = "unknown", "representative_restore_missing"
        if samples:
            latest = max(samples, key=lambda m: m["sequence"])
            required_bytes = sum(
                disk["size_gib"] * 1024**3
                for workload in intent["workloads"]
                for disk in workload["disks"]
                if disk["dataset_id"] == dataset["id"]
            )
            if (
                type(latest["sequence"]) is not int
                or latest["sequence"] < 1
                or type(latest["observed_at"]) is not int
                or not 0 <= now - latest["observed_at"] <= 60
                or latest["expires_at"] <= now
                or latest["profile_digest"] != profile["digest"]
                or latest["generation_id"] != destination["generation_id"]
                or latest["native_scope"] != destination["native_scope"]
                or latest["artifacts"] != policy["artifacts"]
                or latest["policy_sha256"] != digest(policy)
                or latest["storage_backend"] != destination["installed_tuple"]["storage_backend"]
                or latest["method"] != objective["method"]
                or latest["consistency"] != dataset["consistency"]
                or required_bytes <= 0
                or any(
                    type(latest[k]) is not int or latest[k] < 0
                    for k in ("representative_bytes", "load", "parallel_restores")
                )
                or latest["representative_bytes"] < required_bytes
                or latest["load"] < accepted["minimum_load"]
                or latest["load_unit"] != accepted["load_unit"]
                or latest["parallel_restores"] != accepted["parallel_restores"]
                or latest["unit"] != "seconds"
                or not latest["native_restore_id"]
                or not latest["restore_chain_sha256"]
            ):
                reason = "restore_profile_stale_or_unrepresentative"
            elif latest["outcome"] != "passed" or latest["consistency_passed"] is not True:
                status, reason = "blocked", "latest_native_restore_failed"
            else:
                times = [
                    latest[k] for k in (
                        "last_consistent_checkpoint_at", "failure_at", "restore_started_at",
                        "application_ready_at",
                    )
                ]
                if any(type(t) is not int or t < 0 or t > now for t in times):
                    reason = "restore_timing_invalid"
                else:
                    checkpoint, failure, started, ready = times
                    if checkpoint > failure or failure > started or started > ready:
                        reason = "restore_timing_invalid"
                    else:
                        rpo, rto = failure - checkpoint, ready - started
                        passed = (
                            rpo <= objective["rpo_seconds"] and rto <= objective["rto_seconds"]
                        )
                        status = "eligible" if passed else "blocked"
                        reason = "measured_restore_meets_objectives" if passed else (
                            "measured_restore_exceeds_objectives"
                        )
        checks.append(("recovery.measured_objectives", status, reason, mandatory))
    return checks
