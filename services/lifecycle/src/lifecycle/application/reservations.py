"""Durable local intents around independently authoritative owner simulations."""

import json
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from typing import Any, Protocol
from uuid import uuid4

from lifecycle.domain.admission import digest


class Held(Exception):
    pass


class Transaction(Protocol):
    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> None: ...
    def one(self, sql: str, parameters: Sequence[Any] = ()) -> dict[str, Any] | None: ...
    def all(self, sql: str, parameters: Sequence[Any] = ()) -> list[dict[str, Any]]: ...


class Database(Protocol):
    def transaction(self) -> AbstractContextManager[Transaction]: ...


class Owner(Protocol):
    def command(
        self, operation: str, key: str, intent: dict[str, Any], receipt: dict[str, Any] | None
    ) -> dict[str, Any]: ...
    def observe(self, key: str, intent: dict[str, Any]) -> dict[str, Any]: ...


class Reservations:
    def __init__(
        self, database: Database, owners: dict[str, Owner], clock: Callable[[], int]
    ) -> None:
        self.database, self.owners, self.clock = database, owners, clock

    def reserve(
        self, tenant: str, plan_digest: str, intents: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not 1 <= len(intents) <= 32:
            raise Held("intent_bound")
        ids = []
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7503001)")
            for intent in intents:
                if (
                    intent.get("owner") not in self.owners
                    or type(intent.get("amount")) is not int
                    or intent["amount"] < 1
                    or intent["scope"]["tenant_id"] != tenant
                ):
                    raise Held("invalid_owner_intent")
                key = digest({"tenant": tenant, "plan": plan_digest, "intent": intent})
                row = tx.one("SELECT id FROM app.reservation_heads WHERE intent_key=%s", (key,))
                if row is None:
                    identity = str(uuid4())
                    tx.execute(
                        "INSERT INTO app.reservation_heads(id,tenant,plan_digest"
                        ",intent_key,intent,state,revision) "
                        "VALUES(%s,%s,%s,%s,%s::jsonb,'local_intent',1)",
                        (identity, tenant, plan_digest, key, json.dumps(intent)),
                    )
                    self.event(tx, identity, "local_intent", {"plan_digest": plan_digest})
                else:
                    identity = str(row["id"])
                ids.append(identity)
        # An earlier owner success remains held when a later owner fails.
        return [self.command(tenant, identity, "reserve", identity) for identity in ids]

    def read(self, tenant: str, identity: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            row = tx.one(
                "SELECT * FROM app.reservation_heads WHERE id=%s AND tenant=%s", (identity, tenant)
            )
            if row is None:
                raise Held("not_found")
            row["id"] = str(row["id"])
            return row

    def command(self, tenant: str, identity: str, operation: str, key: str) -> dict[str, Any]:
        if operation not in {"reserve", "renew", "confirm", "release", "reconcile"}:
            raise Held("invalid_operation")
        row = self.read(tenant, identity)
        now = self.clock()
        if operation == "reconcile":
            try:
                observation = self.owners[row["intent"]["owner"]].observe(
                    identity, row["intent"] | {"plan_digest": row["plan_digest"]}
                )
                self.validate(observation, row)
            except Exception:
                observation = {"state": "outcome_unknown"}
            with self.database.transaction() as tx:
                tx.execute("SELECT pg_advisory_xact_lock(7503001)")
                # A stale observer cannot overwrite a later completed command.
                latest = tx.one(
                    "SELECT revision FROM app.reservation_heads WHERE id=%s", (identity,)
                )
                if latest is None or latest["revision"] != row["revision"]:
                    raise Held("observation_raced_command")
                self.finish(tx, identity, observation)
            return self.read(tenant, identity)
        payload = digest({"operation": operation, "key": key, "id": identity})
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7503001)")
            current = tx.one(
                "SELECT * FROM app.reservation_heads WHERE id=%s AND tenant=%s", (identity, tenant)
            )
            assert current is not None
            prior = tx.one(
                "SELECT payload FROM app.reservation_commands WHERE tenant=%s AND command_key=%s",
                (tenant, key),
            )
            if prior:
                if prior["payload"] != payload:
                    raise Held("command_key_conflict")
                return self.public(current)
            state = current["state"]
            if state in {"attempting", "outcome_unknown"}:
                raise Held("reconciliation_required")
            if operation == "reserve" and state != "local_intent":
                return self.public(current)
            if operation != "reserve" and state not in {"reserved", "confirmed", "expired_held"}:
                raise Held("invalid_transition")
            receipt = current["receipt"]
            if operation == "release" and (
                receipt is None
                or receipt.get("in_use") is not False
                or receipt.get("observed_at", 0) < now - 5
            ):
                raise Held("unused_owner_observation_required")
            tx.execute(
                "INSERT INTO app.reservation_commands(tenant,command_key"
                ",payload,reservation) VALUES(%s,%s,%s,%s)",
                (tenant, key, payload, identity),
            )
            tx.execute(
                "UPDATE app.reservation_heads SET state='attempting',rev"
                "ision=revision+1 WHERE id=%s",
                (identity,),
            )
            self.event(tx, identity, "attempting", {"operation": operation, "command_key": key})
            row = current
        try:
            observed = self.owners[row["intent"]["owner"]].command(
                operation,
                identity + ":" + key,
                row["intent"] | {"plan_digest": row["plan_digest"]},
                receipt,
            )
            self.validate(observed, row)
        except Exception:
            observed = {"state": "outcome_unknown"}
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7503001)")
            latest = tx.one("SELECT revision FROM app.reservation_heads WHERE id=%s", (identity,))
            if latest is not None and latest["revision"] == row["revision"] + 1:
                self.finish(tx, identity, observed)
            else:
                self.event(tx, identity, "late_owner_receipt", observed)
        return self.read(tenant, identity)

    def expire(self, tenant: str, identity: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7503001)")
            row = tx.one(
                "SELECT * FROM app.reservation_heads WHERE id=%s AND tenant=%s", (identity, tenant)
            )
            if row is None:
                raise Held("not_found")
            if (
                row["receipt"]
                and row["receipt"].get("expires_at", 0) <= self.clock()
                and row["state"] in {"reserved", "confirmed"}
            ):
                tx.execute(
                    "UPDATE app.reservation_heads SET state='expired_held',r"
                    "evision=revision+1 WHERE id=%s",
                    (identity,),
                )
                self.event(tx, identity, "expired_held", {"release_dispatched": False})
        return self.read(tenant, identity)

    def validate(self, receipt: dict[str, Any], row: dict[str, Any]) -> None:
        if (
            receipt.get("state")
            not in {"reserved", "confirmed", "released", "denied", "outcome_unknown"}
            or any(receipt.get(k) != row["intent"][k] for k in ("owner", "kind", "amount", "scope"))
            or receipt.get("reservation_id") != str(row["id"])
            or receipt.get("plan_digest") != row["plan_digest"]
            or receipt.get("observed_at", 0) > self.clock()
            or self.clock() - receipt.get("observed_at", 0) > 5
            or not receipt.get("receipt_id")
        ):
            raise Held("owner_receipt_mismatch")

    def finish(self, tx: Transaction, identity: str, receipt: dict[str, Any]) -> None:
        tx.execute(
            "UPDATE app.reservation_heads SET state=%s,receipt=%s::j"
            "sonb,revision=revision+1 WHERE id=%s",
            (receipt["state"], json.dumps(receipt), identity),
        )
        self.event(tx, identity, receipt["state"], receipt)

    def event(self, tx: Transaction, identity: str, state: str, facts: dict[str, Any]) -> None:
        tx.execute(
            "INSERT INTO app.reservation_events(id,reservation,state"
            ",facts,occurred_at) VALUES(%s,%s,%s,%s::jsonb,%s)",
            (str(uuid4()), identity, state, json.dumps(facts), self.clock()),
        )

    @staticmethod
    def public(row: dict[str, Any]) -> dict[str, Any]:
        return {**row, "id": str(row["id"])}
