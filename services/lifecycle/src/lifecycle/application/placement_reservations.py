"""Atomic vector admission against independently observed, exclusively owned physical pools."""

import json
from collections.abc import Callable
from typing import Any, Protocol
from uuid import uuid4

from lifecycle.application.reservations import Database, Held, Transaction
from lifecycle.domain.admission import digest


class PoolSnapshots(Protocol):
    def pools(self, request: dict[str, Any]) -> list[dict[str, Any]]: ...
    def allocation(self, request: dict[str, Any], reservation_id: str) -> dict[str, Any]: ...


def vector(value: dict[str, Any]) -> dict[str, int]:
    kinds = {"vcpus", "memory_mib", "storage_gib", "addresses"}
    if set(value) != kinds or any(
        type(v) is not int or v < 0 or v > 2**53 - 1 for v in value.values()
    ):
        raise Held("placement_vector_invalid")
    return dict(value)


class PlacementReservations:
    def __init__(
        self, database: Database, snapshots: PoolSnapshots, clock: Callable[[], int]
    ) -> None:
        self.database, self.snapshots, self.clock = database, snapshots, clock

    def event(
        self, tx: Transaction, identity: str, state: str, facts: dict[str, Any]
    ) -> None:
        tx.execute(
            "INSERT INTO app.placement_events(id,reservation,state,facts,occurred_at) "
            "VALUES(%s,%s,%s,%s::jsonb,%s)",
            (str(uuid4()), identity, state, json.dumps(facts), self.clock()),
        )

    def reserve(self, tenant: str, request: dict[str, Any]) -> dict[str, Any]:
        if request["scope"]["tenant_id"] != tenant or not 1 <= len(request["allocations"]) <= 50:
            raise Held("placement_scope_invalid")
        request_digest = digest(request)
        # Exact retries first read durable acceptance; an unavailable observer cannot duplicate it.
        with self.database.transaction() as tx:
            prior = tx.one(
                "SELECT * FROM app.placement_reservations WHERE tenant=%s AND plan_digest=%s",
                (tenant, request["plan_digest"]),
            )
        if prior:
            if prior["request_digest"] != request_digest:
                raise Held("placement_request_conflict")
            return self.receipt(prior)
        pools = self.snapshots.pools(request)
        by_id = {p["id"]: p for p in pools}
        demand: dict[str, dict[str, int]] = {}
        for allocation in request["allocations"]:
            identity = allocation["pool_id"]
            pool = by_id.get(identity)
            if pool is None or allocation["native_ref"] != pool["native_ref"]:
                raise Held("placement_pool_changed")
            if pool["id"] != digest(
                {"provider_id": pool["provider_id"], "native_ref": pool["native_ref"]}
            ):
                raise Held("placement_physical_identity_unverified")
            values = vector(allocation["vector"])
            total = demand.setdefault(identity, {k: 0 for k in values})
            for kind, value in values.items():
                total[kind] += value
        with self.database.transaction() as tx:
            # One authority for physical pool identities; tenant IDs never partition this lock.
            tx.execute("SELECT pg_advisory_xact_lock(7503016)")
            prior = tx.one(
                "SELECT * FROM app.placement_reservations WHERE tenant=%s AND plan_digest=%s",
                (tenant, request["plan_digest"]),
            )
            if prior:
                if prior["request_digest"] != request_digest:
                    raise Held("placement_request_conflict")
                return self.receipt(prior)
            state = "reserved"
            for identity, requested in demand.items():
                pool = by_id[identity]
                if (
                    type(pool["observed_at"]) is not int
                    or not 0 <= self.clock() - pool["observed_at"] <= 5
                    or pool["expires_at"] <= self.clock()
                    or pool["exclusive_owner"] != "lifecycle-resource-owner"
                    or not pool["native_lease_id"]
                    or pool["lease_expires_at"] < self.clock() + 300
                    or pool["policy_sha256"] != request["policy_sha256"]
                    or tenant not in pool["allowed_tenants"]
                ):
                    raise Held("placement_native_authority_unavailable")
                limits, used = vector(pool["limits"]), vector(pool["provider_used"])
                debits = tx.all(
                    "SELECT d.native_ref,d.vector,r.id,r.state FROM app.placement_debits d "
                    "JOIN app.placement_reservations r ON r.id=d.reservation "
                    "WHERE d.pool_id=%s AND r.state NOT IN ('released','denied')",
                    (identity,),
                )
                held = {k: 0 for k in limits}
                for debit in debits:
                    if debit["native_ref"] != pool["native_ref"]:
                        raise Held("placement_pool_identity_collision")
                    # Subtract only once after independent provider readback identifies this token.
                    if (
                        debit["state"] == "confirmed"
                        and str(debit["id"]) in pool["accounted_reservation_ids"]
                    ):
                        continue
                    for kind, value in vector(debit["vector"]).items():
                        held[kind] += value
                if any(used[k] + held[k] + requested[k] > limits[k] for k in limits):
                    state = "denied"
            identity = str(uuid4())
            tx.execute(
                "INSERT INTO app.placement_reservations(id,tenant,plan_digest,request_digest,"
                "request,state,expires_at,revision) VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s,1)",
                (identity, tenant, request["plan_digest"], request_digest, json.dumps(request),
                 state, self.clock() + 300),
            )
            if state == "reserved":
                for pool_id, values in demand.items():
                    tx.execute(
                        "INSERT INTO app.placement_debits(reservation,pool_id,native_ref,vector) "
                        "VALUES(%s,%s,%s,%s::jsonb)",
                        (identity, pool_id, by_id[pool_id]["native_ref"], json.dumps(values)),
                    )
            self.event(tx, identity, state, {"request_digest": request_digest})
        return self.check(tenant, request["plan_digest"])

    def receipt(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "reservation_id": str(row["id"]),
            "tenant_id": str(row["tenant"]),
            "plan_digest": row["plan_digest"],
            "request_digest": row["request_digest"],
            "placement_sha256": row["request"]["placement_sha256"],
            "generation_id": row["request"]["generation_id"],
            "policy_sha256": row["request"]["policy_sha256"],
            "allocations": row["request"]["allocations"],
            "state": row["state"],
            "observed_at": self.clock(),
            "expires_at": row["expires_at"],
            "revision": row["revision"],
            "native_write_authorized": False,
        }

    def check(self, tenant: str, plan_digest: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            row = tx.one(
                "SELECT * FROM app.placement_reservations WHERE tenant=%s AND plan_digest=%s",
                (tenant, plan_digest),
            )
            if row is None:
                raise Held("placement_reservation_missing")
        if row["state"] in {"reserved", "confirmed"} and row["expires_at"] <= self.clock():
            with self.database.transaction() as tx:
                tx.execute("SELECT pg_advisory_xact_lock(7503016)")
                tx.execute(
                    "UPDATE app.placement_reservations SET state='expired_held',revision=revision+1 "
                    "WHERE id=%s AND state IN ('reserved','confirmed') AND expires_at<=%s",
                    (row["id"], self.clock()),
                )
            row["state"] = "expired_held"
        if row["state"] in {"reserved", "confirmed"}:
            pools = self.snapshots.pools(row["request"])
            for allocation in row["request"]["allocations"]:
                candidates = [p for p in pools if p["id"] == allocation["pool_id"]]
                if len(candidates) != 1:
                    raise Held("placement_pool_readback_missing")
                pool = candidates[0]
                if (
                    pool["native_ref"] != allocation["native_ref"]
                    or pool["exclusive_owner"] != "lifecycle-resource-owner"
                    or not pool["native_lease_id"]
                    or pool["lease_expires_at"] <= self.clock()
                    or pool["expires_at"] <= self.clock()
                    or not 0 <= self.clock() - pool["observed_at"] <= 5
                    or pool["policy_sha256"] != row["request"]["policy_sha256"]
                ):
                    raise Held("placement_native_authority_unavailable")
                row["expires_at"] = min(
                    row["expires_at"], pool["expires_at"], pool["lease_expires_at"]
                )
        return self.receipt(row)

    def transition(self, tenant: str, plan_digest: str, operation: str) -> dict[str, Any]:
        if operation not in {"confirm", "renew", "release"}:
            raise Held("placement_operation_invalid")
        with self.database.transaction() as tx:
            row = tx.one(
                "SELECT * FROM app.placement_reservations WHERE tenant=%s AND plan_digest=%s",
                (tenant, plan_digest),
            )
        if row is None or row["state"] not in {"reserved", "confirmed", "expired_held"}:
            raise Held("placement_transition_invalid")
        observed = self.snapshots.allocation(row["request"], str(row["id"]))
        if (
            observed["reservation_id"] != str(row["id"])
            or observed["plan_digest"] != plan_digest
            or observed["placement_sha256"] != row["request"]["placement_sha256"]
            or not 0 <= self.clock() - observed["observed_at"] <= 5
            or observed["expires_at"] <= self.clock()
            or observed["outcome"] != "known"
        ):
            raise Held("placement_allocation_readback_required")
        if operation == "release" and (
            observed["in_use"] is not False or observed["allocations_absent"] is not True
        ):
            raise Held("placement_live_or_unknown_allocation_held")
        if observed["in_use"] is True and (
            observed["allocations_sha256"] != digest(row["request"]["allocations"])
        ):
            raise Held("placement_provider_allocation_changed")
        if operation == "confirm" and observed["in_use"] is not True:
            raise Held("placement_provider_allocation_required")
        state = "released" if operation == "release" else (
            "confirmed" if operation == "confirm" or observed["in_use"] is True else "reserved"
        )
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7503016)")
            changed = tx.one(
                "SELECT revision FROM app.placement_reservations WHERE id=%s", (row["id"],)
            )
            if changed is None or changed["revision"] != row["revision"]:
                raise Held("placement_observation_raced")
            tx.execute(
                "UPDATE app.placement_reservations SET state=%s,expires_at=%s,revision=revision+1 "
                "WHERE id=%s",
                (state, self.clock() + 300, row["id"]),
            )
            self.event(tx, str(row["id"]), state, observed)
        return self.check(tenant, plan_digest)
