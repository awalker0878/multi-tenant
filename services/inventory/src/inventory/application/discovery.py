"Atomic enrollment, collection and observation transitions owned by Inventory."

import time
from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from inventory.application.ports import Database, Policies, Transaction
from inventory.domain.discovery import (
    Actor,
    EnrollmentPolicy,
    Rejected,
    Worker,
    canonical,
    digest,
    identifier,
    number,
    observation,
    resource_identity,
    shape,
    text,
)


def uid() -> str:
    return str(uuid4())


def uuid_value(value: Any) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
    except ValueError:
        raise Rejected("invalid_identity") from None
    return value


class Discovery:
    def __init__(
        self,
        database: Database,
        policies: Policies,
        collection_authority: Callable[[EnrollmentPolicy], None],
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.collection_authority = collection_authority
        self.database = database
        self.policies = policies
        self.clock = clock

    def policy(self, endpoint: dict[str, Any]) -> EnrollmentPolicy:
        p = self.policies.load().get(str(endpoint["policy_id"]))
        if p is None or p.policy_digest != endpoint["policy_digest"] or endpoint["revoked"]:
            raise Rejected("enrollment_unavailable", 409)
        if (p.tenant, p.site, p.epoch, p.worker) != tuple(
            str(endpoint[k]) for k in ("tenant", "site", "epoch", "worker_id")
        ):
            raise Rejected("enrollment_unavailable", 409)
        return p

    def endpoint(self, tx: Transaction, actor: Actor, endpoint: str) -> dict[str, Any]:
        row = tx.one(
            ("SELECT * FROM inventory.endpoints WHERE tenant=%s AND site=%s AND id=%s"),
            (actor.tenant, actor.site, identifier(endpoint)),
        )
        if row is None:
            raise Rejected("not_found", 404)
        return row

    def record(
        self,
        tx: Transaction,
        tenant: str,
        actor: str,
        operation: str,
        resource: str,
        details: dict[str, Any],
    ) -> None:
        at = self.clock()
        tx.execute(
            "INSERT INTO inventory.audit VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)",
            (uid(), tenant, actor, operation, resource, at, canonical(details)),
        )
        tx.execute(
            "INSERT INTO inventory.outbox VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
            (uid(), tenant, resource, "inventory." + operation, at, canonical(details)),
        )

    def command(
        self,
        actor: Actor,
        operation: str,
        body: dict[str, Any],
        key: str,
        endpoint: str | None = None,
        expected: int | None = None,
    ) -> dict[str, Any]:
        required = {
            "enroll": "inventory.admin",
            "renew": "inventory.admin",
            "revoke": "inventory.admin",
            "discover": "inventory.discover",
            "match": "inventory.match",
        }
        if actor.action != required.get(operation) or actor.site is None:
            raise Rejected("action_denied", 403)
        identifier(key)
        bound = digest([operation, actor.site, endpoint, expected, body])
        with self.database.transaction() as tx:
            # One bounded transaction serializes command receipts with queue state.
            tx.execute("SELECT pg_advisory_xact_lock(7404001)")
            prior = tx.one(
                (
                    "SELECT * FROM inventory.commands WHERE tenant=%s AND "
                    "actor=%s AND command_key=%s"
                ),
                (actor.tenant, actor.actor, key),
            )
            if prior:
                if prior["digest"] != bound:
                    raise Rejected("idempotency_conflict", 409)
                return dict(prior["result"])
            if operation == "enroll":
                result = self.enroll(tx, actor, body)
            else:
                row = self.endpoint(tx, actor, endpoint or "")
                if operation in {"renew", "revoke"}:
                    if expected is None:
                        raise Rejected("revision_required", 428)
                    if row["revision"] != expected:
                        raise Rejected("stale_revision", 412)
                if operation == "discover":
                    shape(body, set())
                    p = self.policy(row)
                    if p.platform == "ahv":
                        raise Rejected("collector_not_implemented", 409)
                    if tx.one(
                        (
                            "SELECT id FROM inventory.jobs WHERE endpoint=%s AND "
                            "status IN ('queued','running')"
                        ),
                        (endpoint,),
                    ):
                        raise Rejected("discovery_active", 409)
                    pending = tx.one(
                        (
                            "SELECT count(*) AS n FROM inventory.jobs WHERE "
                            "tenant=%s AND status IN ('queued','running')"
                        ),
                        (actor.tenant,),
                    )
                    if pending and pending["n"] >= 20:
                        raise Rejected("tenant_backpressure", 429)
                    job = uid()
                    now = self.clock()
                    tx.execute(
                        (
                            "INSERT INTO inventory.jobs(id,tenant,endpoint,policy_di"
                            "gest,endpoint_revision,status,created_at,updated_at,nex"
                            "t_at) VALUES (%s,%s,%s,%s,%s,'queued',%s,%s,%s)"
                        ),
                        (
                            job,
                            actor.tenant,
                            endpoint,
                            p.policy_digest,
                            row["revision"],
                            now,
                            now,
                            now,
                        ),
                    )
                    self.record(
                        tx,
                        actor.tenant,
                        actor.actor,
                        "discovery.requested",
                        job,
                        {"endpoint_id": endpoint},
                    )
                    result = {
                        "discovery_id": job,
                        "status": "queued",
                        "native_write_authorized": False,
                    }
                elif operation in {"renew", "revoke"}:
                    shape(body, set())
                    if operation == "renew":
                        p_next = self.policies.load().get(str(row["policy_id"]))
                        if p_next is None:
                            raise Rejected("renewal_not_approved", 403)
                        p = p_next
                        if p is None or (p.tenant, p.site, p.epoch, p.owner) != (
                            actor.tenant,
                            actor.site,
                            str(row["epoch"]),
                            actor.actor,
                        ):
                            raise Rejected("renewal_not_approved", 403)
                        # Preserve history when the native identity changes.
                        if (p.platform, p.native_scope) != (row["platform"], row["native_scope"]):
                            raise Rejected("identity_change_requires_enrollment", 409)
                        tx.execute(
                            (
                                "UPDATE inventory.endpoints SET policy_digest=%s,worker_"
                                "id=%s,revoked=false,revision=revision+1,current_generat"
                                "ion=NULL WHERE id=%s"
                            ),
                            (p.policy_digest, p.worker, endpoint),
                        )
                    else:
                        tx.execute(
                            (
                                "UPDATE inventory.endpoints SET revoked=true,revision=re"
                                "vision+1,current_generation=NULL WHERE id=%s"
                            ),
                            (endpoint,),
                        )
                    tx.execute(
                        (
                            "UPDATE inventory.jobs SET status='partial',reason='enro"
                            "llment_changed',lease_token=NULL,lease_until=NULL,updat"
                            "ed_at=%s WHERE endpoint=%s AND status IN "
                            "('queued','running')"
                        ),
                        (self.clock(), endpoint),
                    )
                    self.record(
                        tx,
                        actor.tenant,
                        actor.actor,
                        "endpoint.changed",
                        endpoint or "",
                        {"operation": operation, "revision": row["revision"] + 1},
                    )
                    result = {
                        "endpoint_id": endpoint,
                        "revision": row["revision"] + 1,
                        "state": "revoked" if operation == "revoke" else "registered",
                        "native_write_authorized": False,
                    }
                elif operation == "match":
                    result = self.match(tx, actor, row, body)
                else:
                    raise Rejected("unknown_operation", 404)
            tx.execute(
                "INSERT INTO inventory.commands VALUES (%s,%s,%s,%s,%s::jsonb)",
                (actor.tenant, actor.actor, key, bound, canonical(result)),
            )
            return result

    def enroll(self, tx: Transaction, actor: Actor, body: dict[str, Any]) -> dict[str, Any]:
        shape(body, {"policy_id", "label"})
        p = self.policies.load().get(identifier(body["policy_id"]))
        if p is None or (p.tenant, p.site, p.owner) != (actor.tenant, actor.site, actor.actor):
            raise Rejected("site_owner_not_approved", 403)
        if tx.one(
            ("SELECT id FROM inventory.endpoints WHERE tenant=%s AND policy_id=%s"),
            (actor.tenant, p.policy_id),
        ):
            raise Rejected("already_enrolled", 409)
        endpoint = uid()
        tx.execute(
            (
                "INSERT INTO inventory.endpoints(id,tenant,site,owner_id"
                ",policy_id,policy_digest,epoch,worker_id,platform,nativ"
                "e_scope,label,revision,created_at) VALUES "
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s)"
            ),
            (
                endpoint,
                actor.tenant,
                p.site,
                p.owner,
                p.policy_id,
                p.policy_digest,
                p.epoch,
                p.worker,
                p.platform,
                p.native_scope,
                text(body["label"], 120),
                self.clock(),
            ),
        )
        self.record(
            tx,
            actor.tenant,
            actor.actor,
            "endpoint.changed",
            endpoint,
            {"operation": "enroll", "policy_digest": p.policy_digest},
        )
        return {
            "endpoint_id": endpoint,
            "revision": 1,
            "state": "registered",
            "native_write_authorized": False,
        }

    def match(
        self, tx: Transaction, actor: Actor, endpoint: dict[str, Any], body: dict[str, Any]
    ) -> dict[str, Any]:
        shape(body, {"resource_id", "application_id", "intent_revision", "generation_id"})
        resource = uuid_value(body["resource_id"])
        application = identifier(body["application_id"])
        revision = identifier(body["intent_revision"])
        generation = identifier(body["generation_id"])
        self.policy(endpoint)
        row = tx.one(
            (
                "SELECT r.*,o.expires_at FROM inventory.resources r JOIN"
                " inventory.observations o ON o.resource=r.id AND "
                "o.generation=%s WHERE r.id=%s AND r.tenant=%s AND "
                "r.endpoint=%s"
            ),
            (generation, resource, actor.tenant, endpoint["id"]),
        )
        if row is None:
            raise Rejected("not_found", 404)
        if (
            str(endpoint["current_generation"]) != generation
            or row["expires_at"] <= self.clock()
            or row["identity_hold"]
            or row["tombstone"]
        ):
            raise Rejected("matching_held", 409)
        match_id = uid()
        existing = tx.one(
            (
                "SELECT id FROM inventory.matches WHERE tenant=%s AND "
                "resource=%s AND application=%s AND revision=%s AND "
                "generation=%s"
            ),
            (actor.tenant, resource, application, revision, generation),
        )
        if existing:
            match_id = str(existing["id"])
        else:
            tx.execute(
                "INSERT INTO inventory.matches VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    match_id,
                    actor.tenant,
                    resource,
                    application,
                    revision,
                    generation,
                    actor.actor,
                    self.clock(),
                ),
            )
            self.record(
                tx,
                actor.tenant,
                actor.actor,
                "match.proposed",
                resource,
                {"match_id": match_id, "application_id": application, "generation_id": generation},
            )
        return {"match_id": match_id, "state": "proposed_unverified", "ownership_granted": False}

    def claim(self, worker: Worker) -> dict[str, Any]:
        policies = self.policies.load()
        now = self.clock()
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7404001)")
            rows = tx.all(
                "SELECT j.*,e.policy_id,e.worker_id AS enrolled_worker,e"
                ".revoked,e.revision,e.epoch,e.site,e.native_scope FROM "
                "inventory.jobs j JOIN inventory.endpoints e ON "
                "e.id=j.endpoint WHERE j.status IN ('queued','running') "
                "ORDER BY j.created_at,j.id LIMIT 1000"
            )
            eligible: list[tuple[dict[str, Any], EnrollmentPolicy]] = []
            for j in rows:
                p = policies.get(str(j["policy_id"]))
                if (
                    p is None
                    or p.policy_digest != j["policy_digest"]
                    or j["revoked"]
                    or j["revision"] != j["endpoint_revision"]
                    or now - j["created_at"] > 3600
                ):
                    tx.execute(
                        (
                            "UPDATE inventory.jobs SET status='partial',reason='enro"
                            "llment_or_collection_expired',lease_token=NULL,lease_un"
                            "til=NULL,updated_at=%s WHERE id=%s"
                        ),
                        (now, j["id"]),
                    )
                    continue
                if p.worker != worker.identity or p.worker_fingerprint != worker.fingerprint:
                    continue
                if j["lease_until"] is not None and j["lease_until"] > now:
                    continue
                if j["lease_until"] is not None:
                    # Abandoned pages count toward the same bounded retry budget.
                    failures = j["failures"] + 1
                    tx.execute(
                        (
                            "UPDATE inventory.jobs SET "
                            "failures=%s,lease_token=NULL,lease_until=NULL WHERE "
                            "id=%s"
                        ),
                        (failures, j["id"]),
                    )
                    j["failures"] = failures
                    if failures >= 3:
                        tx.execute(
                            (
                                "UPDATE inventory.jobs SET status='partial',reason='work"
                                "er_disconnected',updated_at=%s WHERE id=%s"
                            ),
                            (now, j["id"]),
                        )
                        continue
                if j["next_at"] <= now:
                    eligible.append((j, p))
            choices: list[tuple[bool, float, str, dict[str, Any], EnrollmentPolicy]] = []
            for j, p in eligible:
                tx.execute(
                    (
                        "INSERT INTO inventory.budgets(authority,next_at) VALUES"
                        " (%s,0) ON CONFLICT DO NOTHING"
                    ),
                    (p.authority,),
                )
                budget = tx.one(
                    "SELECT * FROM inventory.budgets WHERE authority=%s", (p.authority,)
                )
                assert budget is not None
                active = [
                    r
                    for r in rows
                    if r["lease_until"]
                    and r["lease_until"] > now
                    and (pr := policies.get(str(r["policy_id"]))) is not None
                    and pr.authority == p.authority
                ]
                tenant_active = sum(
                    1
                    for r in rows
                    if str(r["tenant"]) == p.tenant and r["lease_until"] and r["lease_until"] > now
                )
                if (
                    budget["next_at"] > now
                    or len(active) >= p.concurrency
                    or tenant_active >= p.tenant_concurrency
                ):
                    tx.execute(
                        ("UPDATE inventory.budgets SET throttled=throttled+1 WHERE authority=%s"),
                        (p.authority,),
                    )
                    continue
                choices.append(
                    (str(budget["last_tenant"]) == p.tenant, j["updated_at"], str(j["id"]), j, p)
                )
            if not choices:
                return {"job": None, "retry_after": 2}
            _, _, _, j, p = min(choices, key=lambda c: c[:3])
            self.collection_authority(p)
            lease = uid()
            tx.execute(
                (
                    "UPDATE inventory.jobs SET status='running',worker_id=%s"
                    ",lease_token=%s,lease_until=%s,updated_at=%s WHERE "
                    "id=%s"
                ),
                (worker.identity, lease, now + 30, now, j["id"]),
            )
            tx.execute(
                (
                    "UPDATE inventory.budgets SET "
                    "next_at=%s,last_tenant=%s,dispatched=dispatched+1 WHERE"
                    " authority=%s"
                ),
                (now + 60 / p.requests_per_minute, p.tenant, p.authority),
            )
            return {
                "job": {
                    "discovery_id": str(j["id"]),
                    "endpoint_id": str(j["endpoint"]),
                    "policy_id": p.policy_id,
                    "policy_digest": p.policy_digest,
                    "sequence": j["page_count"],
                    "stream": j["stream"],
                    "cursor": j["cursor"],
                    "lease_token": lease,
                    "lease_until": now + 30,
                },
                "retry_after": 0,
            }

    def submit(self, worker: Worker, body: dict[str, Any]) -> dict[str, Any]:
        shape(
            body,
            {
                "discovery_id",
                "lease_token",
                "sequence",
                "observations",
                "next_cursor",
                "terminal",
                "coverage",
                "collected_at",
                "error",
            },
        )
        job_id, lease = identifier(body["discovery_id"]), identifier(body["lease_token"])
        number(body["sequence"], 0, 100)
        bound = digest(body)
        now = self.clock()
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7404001)")
            j = tx.one("SELECT * FROM inventory.jobs WHERE id=%s", (job_id,))
            if j is None:
                raise Rejected("not_found", 404)
            e = tx.one("SELECT * FROM inventory.endpoints WHERE id=%s", (j["endpoint"],))
            assert e is not None
            p = self.policy(e)
            if (
                (p.worker, p.worker_fingerprint) != (worker.identity, worker.fingerprint)
                or j["policy_digest"] != p.policy_digest
                or j["endpoint_revision"] != e["revision"]
            ):
                raise Rejected("worker_scope_denied", 403)
            self.collection_authority(p)
            prior = tx.one("SELECT digest FROM inventory.pages WHERE lease_token=%s", (lease,))
            if prior:
                if prior["digest"] != bound:
                    raise Rejected("page_retry_conflict", 409)
                return {"accepted": True, "discovery_id": job_id, "status": j["status"]}
            if (
                j["status"] != "running"
                or str(j["lease_token"]) != lease
                or j["lease_until"] <= now
                or j["page_count"] != body["sequence"]
            ):
                raise Rejected("stale_lease", 409)
            error = body["error"]
            if error is not None:
                if error not in {
                    "transport_unavailable",
                    "throttled",
                    "permission_denied",
                    "invalid_response",
                    "unsafe_destination",
                    "unsupported_api",
                }:
                    raise Rejected("invalid_error")
                failures = j["failures"] + 1
                status = (
                    "queued"
                    if error in {"transport_unavailable", "throttled"} and failures < 3
                    else "partial"
                )
                tx.execute(
                    (
                        "UPDATE inventory.jobs SET status=%s,reason=%s,failures="
                        "%s,next_at=%s,lease_token=NULL,lease_until=NULL,updated"
                        "_at=%s WHERE id=%s"
                    ),
                    (status, error, failures, now + min(60, 2**failures), now, job_id),
                )
                return {"accepted": True, "discovery_id": job_id, "status": status}
            collected = body["collected_at"]
            if (
                type(collected) not in {int, float}
                or not j["updated_at"] - 2 <= collected <= now + 2
            ):
                raise Rejected("invalid_observation_time")
            items = body["observations"]
            if not isinstance(items, list) or len(items) > 100:
                raise Rejected("page_bound")
            if type(body["terminal"]) is not bool or type(body["coverage"]) is not bool:
                raise Rejected("invalid_coverage")
            if body["terminal"] != (body["next_cursor"] is None):
                raise Rejected("invalid_pagination")
            if body["next_cursor"] is not None:
                text(body["next_cursor"])
                if (
                    not items
                    or body["next_cursor"] == j["cursor"]
                    or body["next_cursor"] != items[-1].get("native_id")
                ):
                    raise Rejected("nonprogressing_cursor")
            seen: set[tuple[str, str]] = set()
            previous = tx.all(
                ("SELECT payload FROM inventory.pages WHERE job=%s ORDER BY sequence"), (job_id,)
            )
            for page in previous:
                seen.update((i["kind"], i["native_id"]) for i in page["payload"]["observations"])
            for item in items:
                valid = observation(item, p.native_scope, p.platform)
                key = (valid["kind"], valid["native_id"])
                if key in seen or valid["kind"] != p.streams[j["stream"]]["kind"]:
                    raise Rejected("duplicate_or_wrong_stream")
                seen.add(key)
            tx.execute(
                "INSERT INTO inventory.pages VALUES (%s,%s,%s,%s,%s::jsonb,%s)",
                (job_id, j["page_count"], lease, bound, canonical(body), collected),
            )
            stream = j["stream"] + int(body["terminal"])
            pages = j["page_count"] + 1
            status, reason = "queued", None
            if not body["coverage"] or not p.coverage_reference:
                status, reason = "partial", "privilege_coverage_unknown"
            elif stream == len(p.streams):
                status = "complete"
                self.publish(tx, j, e, p, [r["payload"] for r in previous] + [body])
            elif pages >= p.max_pages or len(seen) >= 10000:
                status, reason = "partial", "collection_bound"
            tx.execute(
                (
                    "UPDATE inventory.jobs SET status=%s,reason=%s,page_coun"
                    "t=%s,stream=%s,cursor=%s,lease_token=NULL,lease_until=N"
                    "ULL,updated_at=%s,completed_at=%s,next_at=%s WHERE "
                    "id=%s"
                ),
                (
                    status,
                    reason,
                    pages,
                    stream,
                    body["next_cursor"],
                    now,
                    now if status in {"complete", "partial"} else None,
                    now,
                    job_id,
                ),
            )
            if status in {"complete", "partial"}:
                self.record(
                    tx,
                    p.tenant,
                    worker.identity,
                    "discovery.completed",
                    job_id,
                    {
                        "status": status,
                        "reason": reason,
                        "endpoint_id": str(e["id"]),
                        "pages": pages,
                    },
                )
            return {"accepted": True, "discovery_id": job_id, "status": status}

    def publish(
        self,
        tx: Transaction,
        job: dict[str, Any],
        endpoint: dict[str, Any],
        p: EnrollmentPolicy,
        pages: list[dict[str, Any]],
    ) -> None:
        now = self.clock()
        # All pages must still be fresh; a long scan cannot refresh old facts.
        if any(page["collected_at"] + p.freshness_seconds <= now for page in pages):
            raise Rejected("generation_expired", 409)
        generation = str(job["id"])
        observed: list[str] = []
        for page in pages:
            for item in page["observations"]:
                rid = resource_identity(
                    str(endpoint["id"]), p.epoch, item["kind"], item["native_id"]
                )
                observed.append(rid)
                prior = tx.one("SELECT * FROM inventory.resources WHERE id=%s", (rid,))
                hold = item["incarnation"] is None
                if prior:
                    hold = (
                        hold
                        or prior["identity_hold"]
                        or prior["tombstone"]
                        or prior["incarnation"] != item["incarnation"]
                    )
                    tx.execute(
                        (
                            "UPDATE inventory.resources SET last_generation=%s,tombs"
                            "tone=false,identity_hold=%s,absent_count=0 WHERE id=%s"
                        ),
                        (generation, hold, rid),
                    )
                else:
                    tx.execute(
                        (
                            "INSERT INTO inventory.resources(id,tenant,endpoint,kind"
                            ",native_id,incarnation,last_generation,identity_hold) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
                        ),
                        (
                            rid,
                            p.tenant,
                            endpoint["id"],
                            item["kind"],
                            item["native_id"],
                            item["incarnation"],
                            generation,
                            hold,
                        ),
                    )
                tx.execute(
                    ("INSERT INTO inventory.observations VALUES (%s,%s,%s,%s::jsonb,%s,%s)"),
                    (
                        generation,
                        rid,
                        p.tenant,
                        canonical(item),
                        page["collected_at"],
                        page["collected_at"] + p.freshness_seconds,
                    ),
                )
        # Two complete reconciliations are required; partial generations never infer deletion.
        tx.execute(
            (
                "UPDATE inventory.resources SET absent_count=absent_coun"
                "t+1,tombstone=(absent_count+1>=2) WHERE endpoint=%s AND"
                " NOT (id=ANY(%s::uuid[]))"
            ),
            (endpoint["id"], observed),
        )
        tx.execute(
            "UPDATE inventory.endpoints SET current_generation=%s WHERE id=%s",
            (generation, endpoint["id"]),
        )
        self.record(
            tx,
            p.tenant,
            p.worker,
            "observation-generation.published",
            generation,
            {
                "endpoint_id": str(endpoint["id"]),
                "resources": len(observed),
                "policy_digest": p.policy_digest,
                "ownership_granted": False,
            },
        )
