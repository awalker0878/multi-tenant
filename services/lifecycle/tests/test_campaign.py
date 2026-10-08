"""Wave boundaries, resource sharing and durable uncertainty; no native support claim."""

from copy import deepcopy
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from test_migration import MigrationOwners, migration_plan

from lifecycle.application.campaigns import Campaigns
from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.domain.admission import digest
from lifecycle.domain.campaign import (
    PHASES,
    campaign_estimate,
    capacity_holds,
    dependency_order,
    estimate,
    next_window,
    performance_sample,
    schedule,
)
from lifecycle.domain.execution import Rejected


def settings() -> dict[str, Any]:
    return {
        "name": "Ottawa wave",
        "timezone": "America/Toronto",
        "windows": [{"start": 1000, "end": 1900}],
        "cutover_windows": [{"start": 1000, "end": 1900}],
        "blackouts": [],
        "stagger_seconds": 60,
        "max_active": 2,
        "phase_limits": {p: 1 for p in PHASES},
        "failure_limit": 1,
    }


def sample(phase: str = "transfer") -> dict[str, Any]:
    return {
        "route_sha256": digest("route"),
        "phase": phase,
        "bytes": 1024,
        "elapsed_ms": 1000,
        "concurrency": 1,
        "observed_at": 1000,
        "expires_at": 1900,
        "evidence_sha256": digest(phase),
        "production_impact_ok": True,
    }


def member(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        **{k: plan[k] for k in ("plan_id", "plan_revision", "plan_digest", "approval_id")},
        "depends_on": [],
        "route_sha256": digest("route"),
        "sizes": {p: 1024 for p in PHASES},
        "demands": {"staging:" + digest("store"): 3072},
        "outage_group": None,
        "priority": 50,
        "not_before": 1000,
        "deadline": 1900,
        "mode": plan["migration"]["mode"],
        "method": plan["migration"]["method"],
    }


def test_windows_split_blackouts_and_require_whole_duration() -> None:
    s = schedule(settings() | {"blackouts": [{"start": 1100, "end": 1300}]})
    assert next_window(s, 1000, 100) == 1000
    assert next_window(s, 1000, 101) == 1300
    assert next_window(s, 1800, 101) is None
    assert next_window(s, 1100, 1) == 1300


@pytest.mark.parametrize(
    "field,value",
    [
        ("timezone", "unknown/zone"),
        ("max_active", True),
        ("windows", []),
        ("stagger_seconds", -1),
        ("failure_limit", 0),
    ],
)
def test_invalid_schedule_is_rejected(field: str, value: Any) -> None:
    with pytest.raises(Rejected):
        schedule(settings() | {field: value})


def test_dependency_cycles_duplicates_and_unknown_nodes_are_rejected() -> None:
    a, b = str(uuid4()), str(uuid4())
    assert dependency_order([{"id": b, "depends_on": [a]}, {"id": a, "depends_on": []}]) == [a, b]
    for members in (
        [{"id": a, "depends_on": [b]}, {"id": b, "depends_on": [a]}],
        [{"id": a, "depends_on": [b]}],
        [{"id": a, "depends_on": []}, {"id": a, "depends_on": []}],
    ):
        with pytest.raises(Rejected):
            dependency_order(members)


def test_estimates_use_each_stage_and_do_not_extrapolate_concurrency() -> None:
    samples = [performance_sample(sample(p), 1000) for p in PHASES]
    sizes = {p: 2048 for p in PHASES}
    result = estimate(samples, digest("route"), sizes, 1000)
    assert result["phases"]["transfer"] == 3
    assert result["phases"]["validation"] == 2
    assert result["total_seconds"] == 15
    assert len(estimate(samples, digest("route"), sizes, 1000, 2)["holds"]) == 6
    assert len(estimate(samples, digest("other"), sizes, 1000)["holds"]) == 6
    assert len(estimate(samples, digest("route"), sizes, 1900)["holds"]) == 6
    slower = sample("conversion") | {"elapsed_ms": 4000}
    assert estimate([*samples, slower], digest("route"), sizes, 1000)["phases"]["conversion"] == 10


def test_resource_admission_counts_outstanding_allocations() -> None:
    assert capacity_holds({"p": 5}, {"p": 10}, {"p": 6}) == ["p"]
    assert capacity_holds({"p": 5}, {"p": 10}, {"p": 5}) == []
    assert capacity_holds({"unknown": 1}, {"p": 10}, {}) == ["unknown"]


@pytest.mark.parametrize("method", ["APPLICATION_REBUILD_RESTORE", "EXTERNAL_BLOCK_REPLICATION"])
def test_methods_without_a_source_restart_count_the_entire_outage(method: str) -> None:
    m = member(migration_plan()) | {"method": method}
    result = campaign_estimate([sample(p) for p in PHASES], m, settings(), 1000)
    assert result["outage_seconds"] == result["total_seconds"]


def test_measured_outage_cannot_exceed_approved_application_objective(
    database: Any, postgres: dict[str, Any]
) -> None:
    campaigns, plan, m, campaign = prepared(database, postgres)
    plan["migration"]["objectives"]["max_outage_seconds"] = 1
    workflow = NativeWorkflow(database, MigrationOwners(plan), lambda: 1000)
    with pytest.raises(Rejected, match="campaign_outage_objective_exceeded"):
        workflow.admit(plan, str(uuid4()), (campaign, m["id"]))
    assert campaigns.read(plan["scope"]["tenant_id"], campaign)["members"][0]["job_id"] is None


def test_phase_concurrency_requires_every_occupancy_and_ignores_unused_cutover() -> None:
    m = member(migration_plan())
    m["mode"] = "rehearsal"
    s = settings()
    samples = [sample(p) for p in PHASES if p != "cutover"]
    assert campaign_estimate(samples, m, s, 1000)["holds"] == []
    s["phase_limits"]["transfer"] = 2
    assert campaign_estimate(samples, m, s, 1000)["holds"] == [
        "measurement_required_transfer_concurrency_2"
    ]
    samples.append(sample("transfer") | {"concurrency": 2, "elapsed_ms": 8000})
    assert campaign_estimate(samples, m, s, 1000)["phases"]["transfer"] == 10
    result = campaign_estimate(samples, m, s, 1000)
    assert result["outage_seconds"] == result["total_seconds"]


def test_same_timestamp_unsafe_measurement_always_wins() -> None:
    good, bad = sample(), sample() | {"production_impact_ok": False}
    for samples in ([good, bad], [bad, good]):
        assert (
            "production_impact_exceeded_transfer"
            in estimate(samples, digest("route"), {p: 1 for p in PHASES}, 1000)["holds"]
        )


def prepared(
    database: Any, postgres: dict[str, Any]
) -> tuple[Campaigns, dict[str, Any], dict[str, Any], str]:
    plan = migration_plan()
    tenant = plan["scope"]["tenant_id"]
    campaigns = Campaigns(database, lambda: 1000)
    m = member(plan)
    scope = {k: plan["scope"][k] for k in ("site_id", "environment", "resource_id")}
    created = campaigns.create(tenant, plan["actor_id"], scope, settings(), [m], str(uuid4()))
    campaigns.command(tenant, created["id"], plan["actor_id"], str(uuid4()), "schedule", 1)
    for phase in PHASES:
        campaigns.sample(tenant, plan["executor_id"], str(uuid4()), sample(phase))
    with psycopg.connect(**postgres, autocommit=True) as c:
        c.execute("INSERT INTO app.native_control VALUES(1,%s,false)", (plan["epoch"],))
        c.execute(
            "INSERT INTO app.migration_pool_observations "
            "VALUES(%s,%s,%s,10000,false,1000,1900,%s,%s)",
            (str(uuid4()), tenant, next(iter(m["demands"])), digest("capacity"), str(uuid4())),
        )
    return campaigns, plan, m, created["id"]


def test_campaign_admission_and_idempotency_are_atomic(
    database: Any, postgres: dict[str, Any]
) -> None:
    campaigns, plan, m, campaign = prepared(database, postgres)
    workflow = NativeWorkflow(database, MigrationOwners(plan), lambda: 1000)
    key = str(uuid4())
    job = workflow.admit(plan, key, (campaign, m["id"]))
    assert workflow.admit(plan, key, (campaign, m["id"])) == job
    view = campaigns.read(plan["scope"]["tenant_id"], campaign)
    assert view["members"][0]["state"] == "admitted"
    with pytest.raises(Rejected):
        campaigns.read(str(uuid4()), campaign)
    with psycopg.connect(**postgres) as c:
        assert c.execute("SELECT count(*) FROM app.migration_allocations").fetchone() == (1,)


def test_campaign_cannot_change_approved_plan_or_reserve_on_failure(
    database: Any, postgres: dict[str, Any]
) -> None:
    _, plan, m, campaign = prepared(database, postgres)
    original = deepcopy(plan)
    plan["plan_digest"] = digest("changed")
    workflow = NativeWorkflow(database, MigrationOwners(plan), lambda: 1000)
    with pytest.raises(Rejected, match="campaign_native_plan_changed"):
        workflow.admit(plan, str(uuid4()), (campaign, m["id"]))
    with psycopg.connect(**postgres) as c:
        assert c.execute("SELECT count(*) FROM app.native_jobs").fetchone() == (0,)
        assert c.execute("SELECT count(*) FROM app.migration_allocations").fetchone() == (0,)
    assert original["plan_digest"] != plan["plan_digest"]


def test_cancel_keeps_active_allocations_and_stops_queued_starts(
    database: Any, postgres: dict[str, Any]
) -> None:
    campaigns, plan, m, campaign = prepared(database, postgres)
    workflow = NativeWorkflow(database, MigrationOwners(plan), lambda: 1000)
    workflow.admit(plan, str(uuid4()), (campaign, m["id"]))
    tenant = plan["scope"]["tenant_id"]
    campaigns.command(tenant, campaign, plan["actor_id"], str(uuid4()), "cancel", 3)
    with psycopg.connect(**postgres) as c:
        assert c.execute("SELECT count(*) FROM app.migration_allocation_releases").fetchone() == (
            0,
        )
    assert campaigns.read(tenant, campaign)["members"][0]["state"] == "admitted"


def test_pause_revokes_a_prepared_campaign_grant(database: Any, postgres: dict[str, Any]) -> None:
    from lifecycle.domain.native_workflow import api_stage

    campaigns, plan, m, campaign = prepared(database, postgres)
    workflow = NativeWorkflow(database, MigrationOwners(plan), lambda: 1000)
    tenant = plan["scope"]["tenant_id"]
    job = workflow.admit(plan, str(uuid4()), (campaign, m["id"]))
    binding = workflow.prepare(tenant, job, "source_prepare")
    campaigns.command(tenant, campaign, plan["actor_id"], str(uuid4()), "pause", 3)
    with pytest.raises(Rejected, match="campaign_paused"):
        workflow.boundary(
            tenant,
            binding,
            plan["executor_id"],
            "before_api_sequence" if api_stage(plan, "source_prepare") else "before_effect",
        )
    with psycopg.connect(**postgres) as c:
        assert c.execute("SELECT count(*) FROM app.native_redemptions").fetchone() == (0,)


def test_fair_dispatch_reaches_ready_members_behind_waiting_members(
    database: Any, postgres: dict[str, Any]
) -> None:
    from lifecycle.application.campaign_dispatch import CampaignDispatcher

    campaigns, plan, _, old = prepared(database, postgres)
    tenant = plan["scope"]["tenant_id"]
    campaigns.command(tenant, old, plan["actor_id"], str(uuid4()), "cancel", 2)
    first = member(plan) | {"not_before": 1200, "priority": 100}
    second = member(plan)
    scope = {k: plan["scope"][k] for k in ("site_id", "environment", "resource_id")}
    campaign = campaigns.create(
        tenant, plan["actor_id"], scope, settings(), [first, second], str(uuid4())
    )["id"]
    campaigns.command(tenant, campaign, plan["actor_id"], str(uuid4()), "schedule", 1)
    dispatch = CampaignDispatcher(
        campaigns,
        NativeWorkflow(database, MigrationOwners(plan), lambda: 1000),
        lambda tenant, ref: plan,
    )
    assert dispatch.tick(1) == {"admitted": 0, "waiting": 1}
    assert dispatch.tick(1) == {"admitted": 1, "waiting": 0}


def test_pool_pause_applies_to_prepared_work_and_release_requires_independent_cleanup(
    database: Any, postgres: dict[str, Any]
) -> None:
    campaigns, plan, m, campaign = prepared(database, postgres)
    tenant, observer = plan["scope"]["tenant_id"], str(uuid4())
    workflow = NativeWorkflow(database, MigrationOwners(plan), lambda: 1000)
    job = workflow.admit(plan, str(uuid4()), (campaign, m["id"]))
    pool = next(iter(m["demands"]))
    value = {
        "pool_key": pool,
        "capacity": 10000,
        "paused": True,
        "observed_at": 1000,
        "expires_at": 1100,
        "evidence_sha256": digest("pause"),
    }
    key = str(uuid4())
    campaigns.capacity(tenant, observer, key, value)
    campaigns.capacity(tenant, observer, key, value)
    assert workflow.checkpoint(tenant, job)["reason"] == "campaign_resource_observation_required"
    with pytest.raises(Rejected, match="capacity_observation_conflict"):
        campaigns.capacity(tenant, observer, key, value | {"paused": False})
    release = {
        "member_id": m["id"],
        "pool_key": pool,
        "observed_at": 1000,
        "evidence_sha256": digest("cleanup"),
        "unused": True,
        "provider_requests_quiescent": True,
    }
    with pytest.raises(Rejected, match="independent_terminal_cleanup_required"):
        campaigns.release(tenant, observer, release)
    with psycopg.connect(**postgres, autocommit=True) as c:
        c.execute("UPDATE app.migration_members SET state='complete' WHERE id=%s", (m["id"],))
    with pytest.raises(Rejected, match="independent_terminal_cleanup_required"):
        campaigns.release(tenant, plan["executor_id"], release)
    campaigns.release(tenant, observer, release)
    campaigns.release(tenant, observer, release)
    with psycopg.connect(**postgres) as c:
        assert c.execute("SELECT count(*) FROM app.migration_allocation_releases").fetchone() == (
            1,
        )
