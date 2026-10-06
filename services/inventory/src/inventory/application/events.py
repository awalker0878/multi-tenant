"""Confirmed delivery retains original fact identity even after an actor is revoked."""

import time
from collections.abc import Callable
from typing import Any

from inventory.application.ports import Database


def publish_one(database: Database, confirmed: Callable[[dict[str, Any]], None]) -> bool:
    with database.transaction() as tx:
        # Serialize publishers so later events cannot overtake an uncertain fact.
        tx.execute("SELECT pg_advisory_xact_lock(7404002)")
        row = tx.one(
            "SELECT o.* FROM inventory.outbox o LEFT JOIN inventory.delivery d "
            "ON d.event=o.id WHERE d.event IS NULL ORDER BY o.sequence LIMIT 1"
        )
        if row is None:
            return False
        fact = {
            "specversion": "1.0",
            "event_id": str(row["id"]),
            "tenant_id": str(row["tenant"]),
            "aggregate_id": str(row["aggregate"]),
            "event_type": row["event_type"],
            "sequence": row["sequence"],
            "occurred_at": row["at"],
            "data": row["payload"],
        }
        confirmed(fact)
        tx.execute("INSERT INTO inventory.delivery VALUES (%s,%s)", (row["id"], time.time()))
        return True
