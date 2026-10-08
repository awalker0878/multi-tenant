"""Real PostgreSQL journal and independently observed owner allocations; no native resources."""

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from lifecycle.application.reservations import Held, Reservations
from lifecycle.infrastructure.store import Postgres

TENANT = "10000000-0000-4000-8000-000000000001"
NOW = 2_000_000_000


class Owner:
    def __init__(self, parameters: dict[str, Any], name: str = "capacity") -> None:
        self.parameters = parameters
        self.name = name
        self.lose = False
        self.fail = False
        self.now = NOW
        with psycopg.connect(**parameters, autocommit=True) as c:
            c.execute("CREATE SCHEMA IF NOT EXISTS owner_fixture")
            c.execute(
                "CREATE TABLE IF NOT EXISTS owner_fixture.allocations(ow"
                "ner text,id text, receipt jsonb,PRIMARY KEY(owner,id))"
            )
            c.execute("DELETE FROM owner_fixture.allocations WHERE owner=%s", (name,))

    def command(
        self, operation: str, key: str, intent: dict[str, Any], receipt: dict[str, Any] | None
    ) -> dict[str, Any]:
        identity = key.split(":")[0]
        with psycopg.connect(**self.parameters, row_factory=dict_row) as c:
            c.execute("SELECT pg_advisory_xact_lock(7503999)")
            rows = c.execute(
                "SELECT receipt FROM owner_fixture.allocations WHERE owner=%s", (self.name,)
            ).fetchall()
            existing = next(
                (r["receipt"] for r in rows if r["receipt"]["reservation_id"] == identity), None
            )
            if operation == "reserve" and existing:
                return dict(existing)
            state = (
                "denied"
                if self.fail
                or sum(
                    r["receipt"]["amount"]
                    for r in rows
                    if r["receipt"]["state"] in {"reserved", "confirmed"}
                )
                + intent["amount"]
                > 4
                else "reserved"
            )
            if operation != "reserve":
                assert existing is not None
                if operation == "release" and existing["in_use"]:
                    raise Held("owner_live_allocation")
                state = {"renew": existing["state"], "confirm": "confirmed", "release": "released"}[
                    operation
                ]
            result = {k: intent[k] for k in ("owner", "kind", "amount", "scope", "plan_digest")}
            result.update(
                reservation_id=identity,
                receipt_id="receipt-" + identity,
                state=state,
                in_use=state == "confirmed",
                observed_at=self.now,
                expires_at=self.now + 300,
            )
            c.execute(
                "INSERT INTO owner_fixture.allocations(owner,id,receipt)"
                " VALUES(%s,%s,%s::jsonb) ON CONFLICT(owner,id) DO UPDAT"
                "E SET receipt=EXCLUDED.receipt",
                (self.name, identity, json.dumps(result)),
            )
        if self.lose:
            self.lose = False
            raise TimeoutError("reply lost after owner acceptance")
        return result

    def observe(self, key: str, intent: dict[str, Any]) -> dict[str, Any]:
        with psycopg.connect(**self.parameters, row_factory=dict_row) as c:
            row = c.execute(
                "SELECT receipt FROM owner_fixture.allocations WHERE owner=%s AND id=%s",
                (self.name, key),
            ).fetchone()
            assert row is not None
            return dict(row["receipt"], observed_at=self.now)


def intent(owner: str = "capacity") -> dict[str, Any]:
    return {
        "owner": owner,
        "kind": "vcpus",
        "amount": 4,
        "scope": {"tenant_id": TENANT, "site_id": "isolated-lab"},
        "ttl_seconds": 300,
    }


def test_competing_plans_cannot_infer_double_allocation(
    database: Postgres, postgres: dict[str, Any]
) -> None:
    owner = Owner(postgres)
    journal = Reservations(database, {"capacity": owner}, lambda: NOW)
    with ThreadPoolExecutor(2) as pool:
        rows = list(
            pool.map(lambda n: journal.reserve(TENANT, str(n) * 64, [intent()])[0], range(2))
        )
    assert sorted(r["state"] for r in rows) == ["denied", "reserved"]
    with psycopg.connect(**postgres) as c:
        assert c.execute(
            "SELECT sum((receipt->>'amount')::int) FROM owner_fixtur"
            "e.allocations WHERE receipt->>'state'='reserved'"
        ).fetchone() == (4,)


def test_lost_acceptance_reply_reconciles_without_repeat(
    database: Postgres, postgres: dict[str, Any]
) -> None:
    owner = Owner(postgres)
    owner.lose = True
    journal = Reservations(database, {"capacity": owner}, lambda: NOW)
    row = journal.reserve(TENANT, "a" * 64, [intent()])[0]
    assert row["state"] == "outcome_unknown"
    assert journal.reserve(TENANT, "a" * 64, [intent()])[0]["state"] == "outcome_unknown"
    with pytest.raises(Held, match="reconciliation"):
        journal.command(TENANT, row["id"], "release", str(uuid4()))
    assert journal.command(TENANT, row["id"], "reconcile", str(uuid4()))["state"] == "reserved"
    restarted = Reservations(database, {"capacity": owner}, lambda: NOW)
    assert restarted.read(TENANT, row["id"])["receipt"]["receipt_id"] == "receipt-" + row["id"]


def test_partial_owners_keep_known_receipts_for_compensation(
    database: Postgres, postgres: dict[str, Any]
) -> None:
    first, second = Owner(postgres, "capacity"), Owner(postgres, "addresses")
    second.lose = True
    j = Reservations(database, {"capacity": first, "addresses": second}, lambda: NOW)
    rows = j.reserve(TENANT, "b" * 64, [intent(), intent("addresses")])
    assert [r["state"] for r in rows] == ["reserved", "outcome_unknown"]
    assert j.command(TENANT, rows[1]["id"], "reconcile", str(uuid4()))["state"] == "reserved"
    assert j.command(TENANT, rows[0]["id"], "release", str(uuid4()))["state"] == "released"
    assert j.read(TENANT, rows[1]["id"])["state"] == "reserved"


def test_expiry_never_releases_live_and_retry_is_idempotent(
    database: Postgres, postgres: dict[str, Any]
) -> None:
    owner = Owner(postgres)
    j = Reservations(database, {"capacity": owner}, lambda: owner.now)
    row = j.reserve(TENANT, "c" * 64, [intent()])[0]
    key = str(uuid4())
    confirmed = j.command(TENANT, row["id"], "confirm", key)
    assert j.command(TENANT, row["id"], "confirm", key) == confirmed
    owner.now = NOW + 400
    assert j.expire(TENANT, row["id"])["state"] == "expired_held"
    assert owner.observe(row["id"], intent())["in_use"]
    with pytest.raises(Held, match="unused_owner"):
        j.command(TENANT, row["id"], "release", str(uuid4()))
    assert j.command(TENANT, row["id"], "reconcile", str(uuid4()))["receipt"]["in_use"]
    assert (
        j.command(TENANT, row["id"], "renew", str(uuid4()))["receipt"]["expires_at"]
        == owner.now + 300
    )


def test_runtime_cannot_erase_journal_or_read_owner_store(
    database: Postgres, postgres: dict[str, Any]
) -> None:
    Owner(postgres)
    with pytest.raises(psycopg.errors.InsufficientPrivilege), database.transaction() as tx:
        tx.execute("DELETE FROM app.reservation_events")
    with pytest.raises(psycopg.errors.InsufficientPrivilege), database.transaction() as tx:
        tx.execute("SELECT * FROM owner_fixture.allocations")
