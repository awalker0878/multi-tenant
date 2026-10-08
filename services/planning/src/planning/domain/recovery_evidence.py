"""Measured recovery uses failure-trigger-to-verified-readiness, not restore duration."""

from typing import Any

from planning.domain.model import digest


def _review_current(profile: dict[str, Any], observer: str, now: int) -> bool:
    """Bind the published recovery limits to a separate policy reviewer.

    This is an E2 policy/measurement binding; E3 still requires Assurance to
    authenticate the policy reviewer and its native source independently.
    """
    review = profile.get("review")
    if not isinstance(review, dict):
        return False
    values = {k: v for k, v in profile.items() if k != "review"}
    return (
        review.get("decision") == "approved"
        and review.get("profile_sha256") == digest(values)
        and isinstance(review.get("reviewed_by"), str)
        and bool(review["reviewed_by"])
        and isinstance(observer, str)
        and bool(observer)
        and review.get("observer_id") == observer
        and review["reviewed_by"] != observer
        and type(review.get("revision")) is int
        and review["revision"] > 0
        and type(review.get("approved_at")) is int
        and review["approved_at"] <= now
        and type(review.get("expires_at")) is int
        and review["expires_at"] > now
        and all(
            type(profile.get(k)) is int and profile[k] >= 0
            for k in ("maximum_rpo_seconds", "maximum_rto_seconds")
        )
    )


def recovery_checks(
    intent: dict[str, Any],
    destination: dict[str, Any],
    profile: dict[str, Any],
    policy: dict[str, Any],
    data: dict[str, Any],
    now: int,
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
            elif not _review_current(accepted, latest.get("observer_id", ""), now):
                reason = "reviewed_recovery_limits_missing_or_stale"
            elif latest["outcome"] != "passed" or latest["consistency_passed"] is not True:
                status, reason = "blocked", "latest_native_restore_failed"
            else:
                fields = (
                    "last_consistent_checkpoint_at",
                    "failure_at",
                    "restore_started_at",
                    "application_ready_at",
                )
                times = [latest.get(k) for k in fields]
                if any(type(t) is not int or not 0 <= t <= now for t in times):
                    reason = "restore_timing_invalid"
                else:
                    checkpoint, failure, started, ready = times
                    if checkpoint > failure or failure > started or started > ready:
                        reason = "restore_timing_invalid"
                    else:
                        required = {
                            f"{dep['from']}->{dep['to']}"
                            for dep in intent["dependencies"]
                            if dep["strength"] == "required"
                            and dep.get("dataset_id") in (None, dataset["id"])
                        }
                        key = latest.get("key_readiness")
                        application = latest.get("application_readiness")
                        dependencies = latest.get("dependency_readiness")
                        if (
                            not isinstance(key, dict)
                            or not isinstance(application, dict)
                            or not isinstance(dependencies, dict)
                            or not required <= dependencies.keys()
                            or type(key.get("verified_at")) is not int
                            or type(application.get("verified_at")) is not int
                            or any(
                                not isinstance(dependencies.get(name), dict)
                                or type(dependencies[name].get("verified_at")) is not int
                                for name in required
                            )
                        ):
                            reason = "complete_application_readiness_missing"
                        elif (
                            key.get("available") is not True
                            or application.get("verified") is not True
                            or any(dependencies[name].get("verified") is not True for name in required)
                        ):
                            status, reason = "blocked", "recovery_readiness_failed"
                        elif (
                            not key.get("native_ref")
                            or not application.get("native_ref")
                            or any(not dependencies[name].get("native_ref") for name in required)
                            or not failure <= key["verified_at"] <= ready
                            or application["verified_at"] != ready
                            or any(
                                not failure <= dependencies[name]["verified_at"] <= ready
                                for name in required
                            )
                        ):
                            reason = "complete_application_readiness_unverified"
                        else:
                            # The outage starts at the failure/recovery trigger,
                            # even when restore initiation was delayed.
                            rpo, rto = failure - checkpoint, ready - failure
                            passed = (
                                rpo <= objective["rpo_seconds"]
                                and rto <= objective["rto_seconds"]
                                and rpo <= accepted["maximum_rpo_seconds"]
                                and rto <= accepted["maximum_rto_seconds"]
                            )
                            status = "eligible" if passed else "blocked"
                            reason = (
                                "measured_restore_meets_objectives"
                                if passed
                                else "measured_restore_exceeds_objectives"
                            )
        checks.append(("recovery.measured_objectives", status, reason, mandatory))
    return checks
