"""Confirmed outbox and durable invalidation inbox; events carry no execution authority."""

from collections.abc import Callable
from typing import Any

from planning.application.ports import Database


def publish_one(database: Database, confirmed: Callable[[dict[str, Any]], None]) -> bool:
    with database.transaction() as tx:
        tx.execute("SELECT pg_advisory_xact_lock(7504003)")
        row = tx.one(
            "SELECT o.* FROM app.planning_outbox o LEFT JOIN app.pla"
            "nning_deliveries d ON d.id=o.id WHERE d.id IS NULL ORDE"
            "R BY sequence LIMIT 1"
        )
        if row is None:
            return False
        fact = dict(row["payload"], sequence=row["sequence"])
        confirmed(fact)
        tx.execute("INSERT INTO app.planning_deliveries(id) VALUES(%s)", (row["id"],))
        return True
