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
        c.execute(
            "INSERT INTO app.native_control VALUES(1,%s,false)", (plan["epoch"],)
        )
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
