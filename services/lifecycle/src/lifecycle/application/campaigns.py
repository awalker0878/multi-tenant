"""Durable migration wave control; unknown outcomes retain their allocations.

All calls are scoped by the authenticated interface. NativeWorkflow rechecks
actual owner authority at admission and every effect boundary.
"""

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from lifecycle.application.reservations import Database, Transaction
from lifecycle.domain.admission import digest
from lifecycle.domain.campaign import (
    PHASES,
    STAGE_PHASE,
    bounded,
    campaign_estimate,
    capacity_holds,
    dependency_order,
    next_window,
    performance_sample,
    resource_demands,
    schedule,
)
from lifecycle.domain.execution import Rejected, identity
from lifecycle.domain.native_workflow import checksum, exact, integer

LOCK = 7707002  # Same lock as native admission: queue assignment and admission cannot race.


def encode(value: Any) -> str:
    return json.dumps(value, allow_nan=False, separators=(",", ":"))


def load_campaign(tx: Transaction, tenant: str, campaign: str) -> dict[str, Any]:
    row = tx.one(
        "SELECT * FROM app.migration_campaigns WHERE id=%s AND tenant=%s",
        (identity(campaign), identity(tenant)),
    )
    if row is None:
        raise Rejected("not_found", 404)
    return row


def validate_member(value: Any) -> dict[str, Any]:
    exact(
        value,
        {
            "id",
            "plan_id",
            "plan_revision",
            "plan_digest",
            "approval_id",
            "depends_on",
            "route_sha256",
            "sizes",
            "demands",
            "outage_group",
            "priority",
            "not_before",
            "deadline",
            "mode",
            "method",
        },
    )
    for key in ("id", "plan_id", "approval_id"):
        identity(value[key])
    checksum(value["plan_digest"])
    checksum(value["route_sha256"])
    integer(value["plan_revision"], 1)
    bounded(value["priority"], 0, 100)
    integer(value["not_before"])
    integer(value["deadline"], value["not_before"] + 1)
    if value["outage_group"] is not None:
        identity(value["outage_group"])
    if value["mode"] not in {"rehearsal", "cutover"}:
        raise Rejected("campaign_mode_invalid", 422)
    from lifecycle.domain.migration import METHODS

    if value["method"] not in METHODS:
        raise Rejected("campaign_method_invalid", 422)
    exact(value["sizes"], set(PHASES))
    for amount in value["sizes"].values():
        integer(amount)
    resource_demands(value["demands"])
    return dict(value)


class Campaigns:
    def __init__(self, database: Database, clock: Callable[[], int]) -> None:
        self.database, self.clock = database, clock

    def event(
        self, tx: Transaction, campaign: str, actor: str, kind: str, facts: dict[str, Any]
    ) -> None:
        tx.execute(
            "INSERT INTO app.migration_campaign_events VALUES(%s,%s,%s,%s,%s::jsonb,%s)",
            (str(uuid4()), campaign, actor, kind, encode(facts), self.clock()),
        )

    def create(
        self,
        tenant: str,
        actor: str,
        scope: dict[str, Any],
        settings: dict[str, Any],
        members: list[dict[str, Any]],
        key: str,
    ) -> dict[str, Any]:
        identity(tenant)
        identity(actor)
        identity(key)
        exact(scope, {"site_id", "environment", "resource_id"})
        for value in scope.values():
            identity(value)
        settings = schedule(settings)
        order = dependency_order(members)
        for member in members:
            validate_member(member)
        fingerprint = digest([scope, settings, members])
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            prior = tx.one(
                "SELECT * FROM app.migration_campaign_commands WHERE tenant=%s "
                "AND actor=%s AND command_key=%s",
                (tenant, actor, key),
            )
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Rejected("campaign_command_conflict", 409)
                return dict(prior["result"])
            campaign = str(uuid4())
            tx.execute(
                "INSERT INTO "
                "app.migration_campaigns(id,tenant,actor,scope,settings,"
                "fingerprint,state,created_at) "
                "VALUES(%s,%s,%s,%s::jsonb,%s::jsonb,%s,'draft',%s)",
                (
                    campaign,
                    tenant,
                    actor,
                    encode(scope),
                    encode(settings),
                    fingerprint,
                    self.clock(),
                ),
            )
            by_id = {m["id"]: m for m in members}
            for ordinal, member_id in enumerate(order):
                tx.execute(
                    "INSERT INTO "
                    "app.migration_members(id,campaign,tenant,ordinal,specification) "
                    "VALUES(%s,%s,%s,%s,%s::jsonb)",
                    (member_id, campaign, tenant, ordinal, encode(by_id[member_id])),
                )
            result = {
                "id": campaign,
                "revision": 1,
                "state": "draft",
                "tenant_id": tenant,
                "scope": scope,
            }
            self.event(tx, campaign, actor, "created", {"fingerprint": fingerprint})
            tx.execute(
                "INSERT INTO app.migration_campaign_commands VALUES(%s,%s,%s,%s,%s::jsonb)",
                (tenant, actor, key, fingerprint, encode(result)),
            )
            return result

    def command(
        self, tenant: str, campaign: str, actor: str, key: str, action: str, revision: int
    ) -> dict[str, Any]:
        if action not in {"schedule", "pause", "cancel"}:
            raise Rejected("campaign_command_invalid", 422)
        identity(actor)
        identity(key)
        integer(revision, 1)
        fingerprint = digest([campaign, action, revision])
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            row = load_campaign(tx, tenant, campaign)
            prior = tx.one(
                "SELECT * FROM app.migration_campaign_commands WHERE tenant=%s "
                "AND actor=%s AND command_key=%s",
                (tenant, actor, key),
            )
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Rejected("campaign_command_conflict", 409)
                return dict(prior["result"])
            if row["revision"] != revision:
                raise Rejected("campaign_revision_changed", 409)
            if row["state"] in {"cancelled", "complete"}:
                raise Rejected("campaign_terminal", 409)
            state = {"schedule": "scheduled", "pause": "paused", "cancel": "cancelled"}[action]
            tx.execute(
                "UPDATE app.migration_campaigns SET state=%s,revision=revision+1 WHERE id=%s",
                (state, campaign),
            )
            if action == "cancel":
                tx.execute(
                    "UPDATE app.migration_members SET "
                    "state='cancelled',reason='campaign_cancelled' WHERE "
                    "campaign=%s AND state='queued'",
                    (campaign,),
                )
            self.event(tx, campaign, actor, action, {"active_native_jobs_unchanged": True})
            result = {
                "id": campaign,
                "revision": revision + 1,
                "state": state,
                "tenant_id": tenant,
                "scope": row["scope"],
            }
            tx.execute(
                "INSERT INTO app.migration_campaign_commands VALUES(%s,%s,%s,%s,%s::jsonb)",
                (tenant, actor, key, fingerprint, encode(result)),
            )
            return result

    def read(self, tenant: str, campaign: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            row = load_campaign(tx, tenant, campaign)
            members = tx.all(
                "SELECT * FROM app.migration_members WHERE campaign=%s AND "
                "tenant=%s ORDER BY ordinal",
                (campaign, tenant),
            )
            samples = tx.all(
                "SELECT sample FROM app.migration_performance_samples WHERE "
                "tenant=%s AND observed_at>%s ORDER BY observed_at DESC LIMIT 10000",
                (tenant, self.clock() - 7 * 86400),
            )
            return {
                "id": campaign,
                "tenant_id": tenant,
                "scope": row["scope"],
                "settings": row["settings"],
                "revision": row["revision"],
                "state": row["state"],
                "members": [
                    {
                        "id": str(m["id"]),
                        "state": m["state"],
                        "reason": m["reason"],
                        "job_id": str(m["job"]) if m["job"] else None,
                        "specification": m["specification"],
                        "estimate": campaign_estimate(
                            [s["sample"] for s in samples],
                            m["specification"],
                            row["settings"],
                            self.clock(),
                        ),
                    }
                    for m in members
                ],
                "native_write_authorized": False,
            }

    def list(self, tenant: str, scope: dict[str, Any]) -> list[dict[str, Any]]:
        identity(tenant)
        exact(scope, {"site_id", "environment", "resource_id"})
        for value in scope.values():
            identity(value)
        with self.database.transaction() as tx:
            rows = tx.all(
                "SELECT id,state,revision,settings,created_at FROM app.migration_campaigns "
                "WHERE tenant=%s AND scope=%s::jsonb ORDER BY created_at DESC,id DESC LIMIT 101",
                (tenant, encode(scope)),
            )
        return [
            {
                "id": str(r["id"]),
                "state": r["state"],
                "revision": r["revision"],
                "name": r["settings"]["name"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def sample(self, tenant: str, worker: str, key: str, value: dict[str, Any]) -> None:
        performance_sample(value, self.clock())
        identity(tenant)
        identity(worker)
        identity(key)
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            row = tx.one(
                "SELECT fingerprint,tenant,worker FROM "
                "app.migration_performance_samples WHERE id=%s",
                (key,),
            )
            if row:
                if (
                    str(row["tenant"]) != tenant
                    or str(row["worker"]) != worker
                    or row["fingerprint"] != digest(value)
                ):
                    raise Rejected("performance_sample_conflict", 409)
                return
            tx.execute(
                "INSERT INTO app.migration_performance_samples VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s)",
                (
                    key,
                    tenant,
                    value["route_sha256"],
                    worker,
                    encode(value),
                    value["observed_at"],
                    digest(value),
                ),
            )

    def capacity(self, tenant: str, observer: str, key: str, value: dict[str, Any]) -> None:
        exact(
            value,
            {"pool_key", "capacity", "paused", "observed_at", "expires_at", "evidence_sha256"},
        )
        identity(tenant)
        identity(observer)
        identity(key)
        resource_demands({value["pool_key"]: 1})
        bounded(value["capacity"], 0, 2**60)
        checksum(value["evidence_sha256"])
        now = self.clock()
        if type(value["paused"]) is not bool:
            raise Rejected("invalid_capacity_observation", 422)
        if (
            not 0 <= now - integer(value["observed_at"]) <= 60
            or not now < integer(value["expires_at"]) <= value["observed_at"] + 300
        ):
            raise Rejected("capacity_observation_stale", 423)
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            row = tx.one("SELECT * FROM app.migration_pool_observations WHERE id=%s", (key,))
            if row:
                if (
                    str(row["tenant"]) != tenant
                    or str(row["observer"]) != observer
                    or any(row[k] != v for k, v in value.items())
                ):
                    raise Rejected("capacity_observation_conflict", 409)
                return
            tx.execute(
                "INSERT INTO app.migration_pool_observations VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    key,
                    tenant,
                    value["pool_key"],
                    value["capacity"],
                    value["paused"],
                    value["observed_at"],
                    value["expires_at"],
                    value["evidence_sha256"],
                    observer,
                ),
            )

    def release(self, tenant: str, observer: str, value: dict[str, Any]) -> None:
        exact(
            value,
            {
                "member_id",
                "pool_key",
                "observed_at",
                "evidence_sha256",
                "unused",
                "provider_requests_quiescent",
            },
        )
        identity(tenant)
        identity(observer)
        identity(value["member_id"])
        checksum(value["evidence_sha256"])
        resource_demands({value["pool_key"]: 1})
        if (
            value["unused"] is not True
            or value["provider_requests_quiescent"] is not True
            or not 0 <= self.clock() - integer(value["observed_at"]) <= 5
        ):
            raise Rejected("current_unused_capacity_observation_required", 423)
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            member = tx.one(
                "SELECT m.*,j.plan FROM app.migration_members m JOIN app.native_jobs j "
                "ON j.id=m.job WHERE m.id=%s AND m.tenant=%s",
                (value["member_id"], tenant),
            )
            if member is None:
                raise Rejected("not_found", 404)
            if observer == member["plan"]["executor_id"] or member["state"] != "complete":
                raise Rejected("independent_terminal_cleanup_required", 423)
            allocated = tx.one(
                "SELECT amount FROM app.migration_allocations WHERE member=%s AND pool_key=%s",
                (value["member_id"], value["pool_key"]),
            )
            if allocated is None:
                raise Rejected("not_found", 404)
            prior = tx.one(
                "SELECT evidence_sha256 FROM app.migration_allocation_releases "
                "WHERE member=%s AND pool_key=%s",
                (value["member_id"], value["pool_key"]),
            )
            if prior and prior["evidence_sha256"] != value["evidence_sha256"]:
                raise Rejected("capacity_release_conflict", 409)
            if not prior:
                tx.execute(
                    "INSERT INTO app.migration_allocation_releases VALUES(%s,%s,%s,%s)",
                    (value["member_id"], value["pool_key"], value["evidence_sha256"], self.clock()),
                )
                self.event(tx, str(member["campaign"]), observer, "allocation_released", value)

    def eligible(self, tx: Transaction, tenant: str, campaign: str, member: str) -> dict[str, Any]:
        row = load_campaign(tx, tenant, campaign)
        if row["state"] != "scheduled":
            raise Rejected("campaign_not_scheduled", 423)
        members = tx.all(
            "SELECT * FROM app.migration_members WHERE campaign=%s AND tenant=%s",
            (campaign, tenant),
        )
        selected = next((m for m in members if str(m["id"]) == member), None)
        if selected is None:
            raise Rejected("not_found", 404)
        if selected["state"] != "queued":
            raise Rejected("campaign_member_not_queued", 423)
        spec, settings, now = selected["specification"], row["settings"], self.clock()
        states = {str(m["id"]): m["state"] for m in members}
        if any(states[d] != "complete" for d in spec["depends_on"]):
            raise Rejected("campaign_dependency_wait", 423)
        if sum(m["state"] == "held" for m in members) >= settings["failure_limit"]:
            raise Rejected("campaign_failure_limit", 423)
        active = [m for m in members if m["state"] in {"admitted", "held"}]
        if len(active) >= settings["max_active"]:
            raise Rejected("campaign_concurrency_wait", 423)
        if spec["outage_group"]:
            group = tx.one(
                "SELECT id FROM app.migration_members WHERE tenant=%s AND "
                "specification->>'outage_group'=%s AND state IN ('admitted','held') LIMIT 1",
                (tenant, spec["outage_group"]),
            )
            if group:
                raise Rejected("campaign_outage_group_wait", 423)
        if (
            now < spec["not_before"]
            or row["last_started_at"] is not None
            and now < row["last_started_at"] + settings["stagger_seconds"]
        ):
            raise Rejected("campaign_stagger_wait", 423)
        samples = tx.all(
            "SELECT sample FROM app.migration_performance_samples WHERE "
            "tenant=%s AND route_sha256=%s AND observed_at>%s ORDER BY observed_at DESC LIMIT 1000",
            (tenant, spec["route_sha256"], now - 7 * 86400),
        )
        prediction = campaign_estimate([s["sample"] for s in samples], spec, settings, now)
        if prediction["holds"]:
            raise Rejected("campaign_measurement_required", 423)
        duration = prediction["total_seconds"]
        if (
            next_window(settings, now, duration, spec["method"] == "VM_COLD_EXPORT") != now
            or now + duration > spec["deadline"]
        ):
            raise Rejected("campaign_window_wait", 423)
        observations = tx.all(
            "SELECT pool_key,min(capacity) AS capacity,bool_or(paused) AS paused,"
            "min(expires_at) AS expires_at FROM (SELECT DISTINCT ON(tenant,pool_key) "
            "tenant,pool_key,capacity,paused,expires_at FROM app.migration_pool_observations "
            "WHERE pool_key=ANY(%s) ORDER BY tenant,pool_key,observed_at DESC,"
            "paused DESC,capacity,expires_at) latest "
            "GROUP BY pool_key HAVING bool_or(tenant=%s)",
            (list(spec["demands"]), tenant),
        )
        capacity = {
            o["pool_key"]: o["capacity"]
            for o in observations
            if o["expires_at"] > now and not o["paused"]
        }
        allocations = tx.all(
            "SELECT a.pool_key,sum(a.amount) AS amount FROM "
            "app.migration_allocations a LEFT JOIN "
            "app.migration_allocation_releases r USING(member,pool_key) WHERE "
            "r.member IS NULL GROUP BY a.pool_key"
        )
        if capacity_holds(
            spec["demands"], capacity, {a["pool_key"]: int(a["amount"]) for a in allocations}
        ):
            raise Rejected("campaign_capacity_wait", 423)
        return selected

    def attach(
        self,
        tx: Transaction,
        tenant: str,
        campaign: str,
        member: str,
        plan: dict[str, Any],
        job: str,
    ) -> None:
        selected = self.eligible(tx, tenant, campaign, member)
        spec = selected["specification"]
        row = load_campaign(tx, tenant, campaign)
        if (
            any(
                plan[k] != spec[k]
                for k in ("plan_id", "plan_revision", "plan_digest", "approval_id")
            )
            or any(plan["scope"][k] != v for k, v in row["scope"].items())
            or plan["actor_id"] != str(row["actor"])
            or plan["purpose"] != "migrate"
            or any(plan["migration"][k] != spec[k] for k in ("mode", "method"))
        ):
            raise Rejected("campaign_native_plan_changed", 423)
        for pool, amount in spec["demands"].items():
            tx.execute(
                "INSERT INTO app.migration_allocations VALUES(%s,%s,%s,%s)",
                (member, pool, amount, self.clock()),
            )
        tx.execute(
            "UPDATE app.migration_members SET job=%s,state='admitted',started_at=%s WHERE id=%s",
            (job, self.clock(), member),
        )
        tx.execute(
            "UPDATE app.migration_campaigns SET last_started_at=%s,revision=revision+1 WHERE id=%s",
            (self.clock(), campaign),
        )
        self.event(
            tx, campaign, plan["actor_id"], "member_admitted", {"member": member, "job": job}
        )


def campaign_boundary(tx: Transaction, job: str, stage: str, now: int) -> dict[str, Any] | None:
    member = tx.one(
        "SELECT m.*,c.settings,c.state AS campaign_state FROM "
        "app.migration_members m JOIN app.migration_campaigns c ON c.id=m.campaign WHERE m.job=%s",
        (job,),
    )
    if member is None:
        return None  # Standalone plans retain their independently approved admission path.
    if member["campaign_state"] != "scheduled":
        raise Rejected("campaign_paused", 423)
    phase = STAGE_PHASE.get(stage)
    if phase is None:
        raise Rejected("campaign_stage_not_supported", 423)
    if (
        next_window(
            member["settings"],
            now,
            1,
            phase == "cutover" or member["specification"]["method"] == "VM_COLD_EXPORT",
        )
        != now
    ):
        raise Rejected("campaign_window_closed", 423)
    # Capacity/impact stops apply to an already prepared grant as well as new admissions.
    samples = tx.all(
        "SELECT sample FROM app.migration_performance_samples WHERE tenant=%s "
        "AND route_sha256=%s AND observed_at>%s ORDER BY observed_at DESC LIMIT 1000",
        (member["tenant"], member["specification"]["route_sha256"], now - 7 * 86400),
    )
    prediction = campaign_estimate(
        [s["sample"] for s in samples], member["specification"], member["settings"], now
    )
    if prediction["phases"][phase] is None:
        raise Rejected("campaign_stage_measurement_required", 423)
    observations = tx.all(
        "SELECT DISTINCT ON(tenant,pool_key) tenant,pool_key,paused,expires_at "
        "FROM app.migration_pool_observations WHERE pool_key=ANY(%s) "
        "ORDER BY tenant,pool_key,observed_at DESC,paused DESC,expires_at",
        (list(member["specification"]["demands"]),),
    )
    if any(o["paused"] or o["expires_at"] <= now for o in observations) or {
        o["pool_key"] for o in observations if str(o["tenant"]) == str(member["tenant"])
    } != set(member["specification"]["demands"]):
        raise Rejected("campaign_resource_observation_required", 423)
    return member


def stage_admission(tx: Transaction, job: str, stage: str, operation: str | None, now: int) -> None:
    member = campaign_boundary(tx, job, stage, now)
    if member is None:
        return
    phase = STAGE_PHASE[stage]
    active = tx.all(
        "SELECT m.campaign,c.settings FROM app.migration_stage_slots s JOIN "
        "app.migration_members m ON m.id=s.member JOIN app.migration_campaigns c "
        "ON c.id=m.campaign "
        "LEFT JOIN "
        "app.migration_stage_releases r ON r.operation=s.operation WHERE "
        "m.specification->>'route_sha256'=%s AND s.phase=%s AND r.operation IS NULL",
        (member["specification"]["route_sha256"], phase),
    )
    limit = min(
        min(r["settings"]["max_active"], r["settings"]["phase_limits"][phase])
        for r in [member, *active]
    )
    if len(active) >= limit:
        raise Rejected("campaign_stage_capacity_wait", 423)
    prior_phase = tx.one(
        "SELECT operation FROM app.migration_stage_slots WHERE member=%s AND phase=%s LIMIT 1",
        (member["id"], phase),
    )
    if phase == "cutover" and prior_phase is None:
        samples = tx.all(
            "SELECT sample FROM app.migration_performance_samples WHERE tenant=%s "
            "AND route_sha256=%s AND observed_at>%s ORDER BY observed_at DESC LIMIT 1000",
            (member["tenant"], member["specification"]["route_sha256"], now - 7 * 86400),
        )
        prediction = campaign_estimate(
            [s["sample"] for s in samples], member["specification"], member["settings"], now
        )
        duration = prediction["phases"]["cutover"]
        if duration is None:
            raise Rejected("campaign_cutover_measurement_required", 423)
        if next_window(member["settings"], now, duration, True) != now:
            raise Rejected("campaign_cutover_window_wait", 423)
    if operation is not None:
        tx.execute(
            "INSERT INTO app.migration_stage_slots VALUES(%s,%s,%s,%s)",
            (operation, member["id"], phase, now),
        )


def stage_complete(tx: Transaction, job: str, operation: str, terminal: bool, now: int) -> None:
    slot = tx.one("SELECT member FROM app.migration_stage_slots WHERE operation=%s", (operation,))
    if slot:
        tx.execute(
            "INSERT INTO app.migration_stage_releases VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (operation, now),
        )
    if terminal:
        tx.execute(
            "UPDATE app.migration_members SET state='complete',completed_at=%s WHERE job=%s",
            (now, job),
        )
        tx.execute(
            "UPDATE app.migration_campaigns c SET state='complete',revision=revision+1 "
            "WHERE c.state='scheduled' AND c.id IN "
            "(SELECT campaign FROM app.migration_members WHERE job=%s) "
            "AND NOT EXISTS (SELECT 1 FROM app.migration_members m WHERE m.campaign=c.id "
            "AND m.state NOT IN ('complete','cancelled'))",
            (job,),
        )
    # Storage and rollback allocations survive completion until separately observed cleanup.
