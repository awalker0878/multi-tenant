"""Bounded synchronous compilation with immutable owned records and atomic outbox."""

import hashlib
import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from planning.application.ports import Database, Sources, Transaction
from planning.application.validation import PlanValidation
from planning.domain.assessment import assess
from planning.domain.placement import fit
from planning.domain.compilation import bind, compile_plan
from planning.domain.model import Actor, Rejected, canonical, digest, identifier, integer, shape


class Planning:
    __slots__ = ("database", "sources", "clock", "_validation")

    def __init__(
        self,
        database: Database,
        sources: Sources,
        clock: Callable[[], int],
        validation: PlanValidation,
    ) -> None:
        if not isinstance(validation, PlanValidation):
            raise ValueError("required_plan_validation")
        self.database, self.sources, self.clock = database, sources, clock
        self._validation = validation

    @property
    def validation(self) -> PlanValidation:
        return self._validation

    def get(
        self, tenant: str, application: str, environment: str, identity: str, kind: str
    ) -> dict[str, Any]:
        with self.database.transaction() as tx:
            row = tx.one(
                (
                    "SELECT payload FROM app.planning_records WHERE id=%s AND "
                    "tenant=%s AND application=%s AND environment=%s AND kind=%s"
                ),
                (identifier(identity), tenant, application, environment, kind),
            )
            if row is None:
                raise Rejected("not_found", 404)
            return dict(row["payload"])

    def retry(
        self, tx: Transaction, actor: Actor, key: str, fingerprint: str
    ) -> dict[str, Any] | None:
        row = tx.one(
            (
                "SELECT fingerprint,response FROM app.planning_commands WHERE "
                "tenant=%s AND actor=%s AND command_key=%s"
            ),
            (actor.tenant, actor.actor, identifier(key)),
        )
        if row:
            if row["fingerprint"] != fingerprint:
                raise Rejected("command_key_conflict", 409)
            return dict(row["response"])
        return None

    def save(
        self, actor: Actor, key: str, fingerprint: str, kind: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        serialized = canonical(payload)
        if len(serialized.encode()) > 900000:
            raise Rejected("assessment_result_bound", 413)
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7504001)")
            prior = self.retry(tx, actor, key, fingerprint)
            if prior:
                return prior
            count = tx.one(
                "SELECT count(*) AS n FROM app.planning_commands WHERE tenant=%s AND created_at>%s",
                (actor.tenant, self.clock() - 60),
            )
            if count and count["n"] >= 30:
                raise Rejected("tenant_command_budget", 429)
            response = {
                "id": payload["id"],
                "kind": kind,
                "digest": digest(payload),
                "native_write_authorized": False,
            }
            if kind == "plan":
                response["binding"] = payload["binding"]
            tx.execute(
                (
                    "INSERT INTO "
                    "app.planning_records(id,tenant,actor,application,enviro"
                    "nment,kind,payload,digest,created_at) VALUES(%s,%s,%s,%"
                    "s,%s,%s,%s::jsonb,%s,%s)"
                ),
                (
                    payload["id"],
                    actor.tenant,
                    actor.actor,
                    actor.application,
                    actor.environment,
                    kind,
                    canonical(payload),
                    response["digest"],
                    self.clock(),
                ),
            )
            tx.execute(
                (
                    "INSERT INTO "
                    "app.planning_commands(tenant,actor,command_key,fingerpr"
                    "int,response,created_at) VALUES(%s,%s,%s,%s,%s::jsonb,%"
                    "s)"
                ),
                (actor.tenant, actor.actor, key, fingerprint, canonical(response), self.clock()),
            )
            event = {
                "specversion": "1.0",
                "event_id": str(uuid4()),
                "tenant_id": actor.tenant,
                "event_type": "planning." + kind + ".created",
                "aggregate_id": payload["id"],
                "occurred_at": self.clock(),
                "data": response,
            }
            tx.execute(
                "INSERT INTO app.planning_outbox(id,tenant,payload) VALUES(%s,%s,%s::jsonb)",
                (event["event_id"], actor.tenant, canonical(event)),
            )
            return response

    def assessment(
        self, actor: Actor, key: str, body: dict[str, Any], delegations: dict[str, str]
    ) -> dict[str, Any]:
        shape(body, {"revision_id", "candidates", "action", "method"})
        fingerprint = digest(
            {
                "operation": "assessment",
                "application": actor.application,
                "environment": actor.environment,
                "body": body,
            }
        )
        with self.database.transaction() as tx:
            prior = self.retry(tx, actor, key, fingerprint)
            if prior:
                return prior
        intent, inputs = self.sources.resolve(
            actor,
            identifier(body["revision_id"]),
            body["candidates"],
            delegations,
            body["action"],
            body["method"],
        )
        now = self.clock()
        results = [
            assess(
                intent["intent"],
                row["destination"],
                row["profile"],
                row["policy"],
                row["qualification"],
                body["action"],
                body["method"],
                now,
            )
            for row in inputs
        ]
        payload = {
            "id": str(uuid4()),
            "tenant_id": actor.tenant,
            "application_id": actor.application,
            "environment": actor.environment,
            "created_at": now,
            "intent": intent,
            "inputs": inputs,
            "results": results,
            "candidates": body["candidates"],
            "action": body["action"],
            "method": body["method"],
        }
        return self.save(actor, key, fingerprint, "assessment", payload)

    def plan(
        self, actor: Actor, key: str, body: dict[str, Any], assessment: dict[str, Any]
    ) -> dict[str, Any]:
        shape(body, {"assessment_id", "candidate", "request"})
        fingerprint = digest(
            {
                "operation": "plan",
                "application": actor.application,
                "environment": actor.environment,
                "body": body,
            }
        )
        with self.database.transaction() as tx:
            prior = self.retry(tx, actor, key, fingerprint)
            if prior:
                return prior
        if body["assessment_id"] != assessment["id"]:
            raise Rejected("assessment_changed", 409)
        candidate = integer(body["candidate"], 0, len(assessment["results"]) - 1)
        identity = str(uuid4())
        content = compile_plan(assessment, candidate, body["request"])
        binding = bind(content, identity, actor.actor)
        payload = {
            "id": identity,
            "assessment_id": assessment["id"],
            "content": content,
            "binding": binding,
            "candidates": [assessment["candidates"][candidate]],
            "candidate": candidate,
            "application_id": actor.application,
            "environment": actor.environment,
            "tenant_id": actor.tenant,
        }
        return self.save(actor, key, fingerprint, "plan", payload)

    def validity(
        self, actor: Actor, plan: dict[str, Any], delegations: dict[str, str]
    ) -> dict[str, Any]:
        content = plan["content"]
        holds = list(content["holds"])
        if "native_provisioning" in content:
            try:
                self.check_native_recipe(plan)
            except Rejected as error:
                holds.append(error.reason)
        if "native_migration" in content:
            try:
                self.validation.migration.current(actor, plan, delegations)
            except Rejected as error:
                holds.append(error.reason)
        try:
            intent, inputs = self.sources.resolve(
                actor,
                content["intent_revision"],
                plan["candidates"],
                delegations,
                content["action"],
                content["method"],
            )
            row = inputs[0]
            current = assess(
                intent["intent"],
                row["destination"],
                row["profile"],
                row["policy"],
                row["qualification"],
                content["action"],
                content["method"],
                self.clock(),
            )
            changed = [
                k
                for k, v in current["input_digests"].items()
                if content["input_digests"].get(k) != v
            ]
            holds += ["input_changed:" + k for k in changed]
            holds += [
                f["reason"]
                for f in current["findings"]
                if f["mandatory"] and f["status"] != "eligible"
            ]
        except Rejected as e:
            if e.status in {401, 403, 404}:
                raise
            holds.append("source_authority_unavailable")
        if min(content["valid_until"], content["input_fresh_until"]) <= self.clock():
            holds.append("plan_or_facts_expired")
        with self.database.transaction() as tx:
            invalidations = tx.all(
                (
                    "SELECT event_id FROM app.planning_invalidations WHERE "
                    "tenant=%s AND plan=%s LIMIT 100"
                ),
                (actor.tenant, plan["id"]),
            )
        if invalidations:
            holds.append("owner_change_requires_new_assessment")
        return {
            "current": not holds,
            "holds": sorted(set(holds)),
            "evaluated_at": self.clock(),
            "approval_digest": plan["binding"]["digest"],
            "native_write_authorized": False,
        }

    def check_native_recipe(self, record: dict[str, Any]) -> None:
        if record["content"]["lane"] == "operational" and (
            "native_provisioning" in record["content"] or "native_migration" in record["content"]
        ):
            self.validation.support_current(record)
        if "native_provisioning" in record["content"]:
            self.validation.native.current(record)
        if "native_migration" in record["content"]:
            self.validation.migration.execution_current(record)
            if (
                min(record["content"]["valid_until"], record["content"]["input_fresh_until"])
                <= self.clock()
            ):
                raise Rejected("migration_plan_expired", 423)

    def placement_proposal(
        self, tenant: str, identity: str, revision: int
    ) -> dict[str, Any]:
        """Expose a deterministic witness; a proposal is never an owner receipt."""
        if revision != 1:
            raise Rejected("not_found", 404)
        with self.database.transaction() as tx:
            row = tx.one(
                "SELECT payload FROM app.planning_records WHERE id=%s AND tenant=%s "
                "AND kind='plan'", (identifier(identity), identifier(tenant)),
            )
            if row is None:
                raise Rejected("not_found", 404)
            plan = row["payload"]
            retained = tx.one(
                "SELECT payload FROM app.planning_records WHERE id=%s AND tenant=%s "
                "AND kind='assessment'", (plan["assessment_id"], tenant),
            )
        content = plan["content"]
        if (
            retained is None or content["execution_ready"] is not True
            or content["lane"] != "operational"
            or min(content["valid_until"], content["input_fresh_until"]) <= self.clock()
        ):
            raise Rejected("placement_proposal_held", 423)
        assessment = retained["payload"]
        inputs = assessment["inputs"][plan["candidate"]]
        try:
            placed = fit(
                assessment["intent"]["intent"],
                inputs["destination"]["capability_snapshot"]["data"]["pools"],
                inputs["policy"], self.clock(),
            )
        except (KeyError, TypeError, ValueError):
            raise Rejected("placement_proposal_unverified", 423) from None
        if placed["status"] != "eligible":
            raise Rejected("placement_proposal_unfit", 423)
        return {
            "scope": content["scope"],
            "plan_id": plan["id"],
            "plan_revision": 1,
            "plan_digest": plan["binding"]["digest"],
            "generation_id": content["inventory_generation"],
            "policy_sha256": digest(inputs["policy"]),
            "placement_sha256": digest(placed["allocations"]),
            "allocations": placed["allocations"],
            "native_write_authorized": False,
        }

    def bound_plan(self, identity: str, revision: int) -> dict[str, Any]:
        if revision != 1:
            raise Rejected("not_found", 404)
        with self.database.transaction() as tx:
            row = tx.one(
                "SELECT payload FROM app.planning_records WHERE id=%s AND kind='plan'",
                (identifier(identity),),
            )
            if row is None:
                raise Rejected("not_found", 404)
            self.check_native_recipe(row["payload"])
            return dict(row["payload"]["binding"])

    def execution_plan(self, tenant: str, identity_value: str, revision: int) -> dict[str, Any]:
        if revision != 1:
            raise Rejected("not_found", 404)
        with self.database.transaction() as tx:
            row = tx.one(
                "SELECT payload FROM app.planning_records WHERE id=%s AN"
                "D tenant=%s AND kind='plan'",
                (identifier(identity_value), identifier(tenant)),
            )
            if row is None:
                raise Rejected("not_found", 404)
            self.check_native_recipe(row["payload"])
            invalidated = tx.one(
                "SELECT event_id FROM app.planning_invalidations WHERE plan=%s LIMIT 1",
                (identity_value,),
            )
            return {
                "content": row["payload"]["content"],
                "binding": row["payload"]["binding"],
                "invalidated": invalidated is not None,
            }

    def invalidate(self, event: dict[str, Any]) -> bool:
        """Broker hints invalidate only; direct owner reads still decide current validity."""
        event_id = identifier(event["event_id"])
        tenant = identifier(event["tenant_id"])
        fingerprint = hashlib.sha256(
            json.dumps(
                event, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
            ).encode()
        ).hexdigest()
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7504002)")
            prior = tx.one(
                "SELECT digest FROM app.planning_fact_inbox WHERE event_id=%s", (event_id,)
            )
            if prior:
                if prior["digest"] != fingerprint:
                    raise Rejected("event_id_conflict", 409)
                return False
            tx.execute(
                (
                    "INSERT INTO "
                    "app.planning_fact_inbox(event_id,tenant,digest,envelope) "
                    "VALUES(%s,%s,%s,%s::jsonb)"
                ),
                (event_id, tenant, fingerprint, json.dumps(event)),
            )
            # Conservative tenant invalidation is safe for unexpanded event contracts.
            # Events never refresh timestamps, confer support, or execute a plan.
            tx.execute(
                (
                    "INSERT INTO "
                    "app.planning_invalidations(tenant,plan,event_id) SELECT "
                    "tenant,id,%s FROM app.planning_records WHERE tenant=%s AND "
                    "kind='plan'"
                ),
                (event_id, tenant),
            )
        return True
