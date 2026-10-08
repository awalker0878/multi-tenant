"""A10/A11 E2: durable out-of-order Assurance invalidation and tenant holds."""

import json
from typing import Any
from uuid import uuid4

import pytest

from planning.application.qualification_invalidations import QualificationInvalidations
from planning.domain.model import Rejected
from planning.infrastructure.store import Postgres


def event(tenant: str, scope: str, epoch: int, operation: str = "suspend") -> dict[str, Any]:
    state = {
        "publish": "qualified",
        "restore": "qualified",
        "suspend": "suspended",
        "revoke": "revoked",
    }[operation]
    return {
        "event_id": str(uuid4()),
        "tenant_id": tenant,
        "scope_sha256": scope,
        "authority_epoch": epoch,
        "operation": operation,
        "state": state,
        "decision_sha256": "a" * 64,
        "event_sha256": str(epoch).zfill(64),
    }


def add_plan(database: Postgres, tenant: str) -> str:
    identity = str(uuid4())
    with database.transaction() as tx:
        tx.execute(
            "INSERT INTO app.planning_records "
            "(id,tenant,actor,application,environment,kind,payload,digest,created_at) "
            "VALUES(%s,%s,%s,%s,%s,'plan',%s::jsonb,%s,%s)",
            (
                identity,
                tenant,
                str(uuid4()),
                str(uuid4()),
                str(uuid4()),
                json.dumps({"id": identity}),
                "b" * 64,
                100,
            ),
        )
    return identity


def test_duplicate_delivery_and_scope_epoch_conflict(database: Postgres) -> None:
    tenant, other = str(uuid4()), str(uuid4())
    plan, foreign = add_plan(database, tenant), add_plan(database, other)
    inbox = QualificationInvalidations(database)
    first = event(tenant, "a" * 64, 1, "publish")
    ack = inbox.accept(first)
    assert ack == {
        "persisted": True,
        "event_id": first["event_id"],
        "scope_sha256": first["scope_sha256"],
        "authority_epoch": 1,
        "event_sha256": first["event_sha256"],
    }
    assert inbox.accept(first) == ack
    with database.transaction() as tx:
        a = tx.one(
            "SELECT count(*) AS n FROM app.planning_invalidations WHERE plan=%s", (plan,)
        )
        b = tx.one(
            "SELECT count(*) AS n FROM app.planning_invalidations WHERE plan=%s", (foreign,)
        )
        assert a is not None and a["n"] == 1
        assert b is not None and b["n"] == 0

    changed = dict(first, state="revoked")
    with pytest.raises(Rejected, match="invalid_qualification_invalidation"):
        inbox.accept(changed)
    changed = dict(first, decision_sha256="c" * 64)
    with pytest.raises(Rejected, match="invalidation_event_conflict"):
        inbox.accept(changed)
    with pytest.raises(Rejected, match="invalidation_epoch_conflict"):
        inbox.accept(event(tenant, "a" * 64, 1))


def test_reordered_epochs_and_restoration_cannot_clear_prior_plan_holds(
    database: Postgres,
) -> None:
    tenant, scope = str(uuid4()), "e" * 64
    plan = add_plan(database, tenant)
    inbox = QualificationInvalidations(database)
    # Deliberate transport reordering: no stale event can roll head backwards.
    for incoming in [
        event(tenant, scope, 3, "revoke"),
        event(tenant, scope, 1, "publish"),
        event(tenant, scope, 2, "suspend"),
        event(tenant, scope, 4, "restore"),
    ]:
        assert inbox.accept(incoming)["persisted"] is True
    with database.transaction() as tx:
        head = tx.one(
            "SELECT authority_epoch,state FROM app.planning_qualification_heads "
            "WHERE scope_sha256=%s",
            (scope,),
        )
        held = tx.one(
            "SELECT count(*) AS n FROM app.planning_invalidations WHERE plan=%s",
            (plan,),
        )
        assert head is not None and head["authority_epoch"] == 4
        assert head["state"] == "qualified"
        assert held is not None and held["n"] == 4

    # The latest positive event remains only a hint, not an automatic hold release.
    assert inbox.accept(event(tenant, "f" * 64, 1, "publish"))["persisted"] is True
    with database.transaction() as tx:
        remaining = tx.one(
            "SELECT count(*) AS n FROM app.planning_invalidations WHERE plan=%s",
            (plan,),
        )
        assert remaining is not None and remaining["n"] == 5


@pytest.mark.parametrize("fault", ["boolean_epoch", "foreign_tenant", "bad_scope", "invalid_operation"])
def test_invalid_wire_semantics_never_create_qualification(fault: str, database: Postgres) -> None:
    tenant, scope = str(uuid4()), "d" * 64
    inbox = QualificationInvalidations(database)
    original = event(tenant, scope, 1)
    if fault == "boolean_epoch":
        original["authority_epoch"] = True
    elif fault == "foreign_tenant":
        original["tenant_id"] = "not-a-uuid"
    elif fault == "bad_scope":
        original["scope_sha256"] = "not-a-sha256"
    else:
        original["operation"] = "unknown"
    with pytest.raises(Rejected):
        inbox.accept(original)
    with database.transaction() as tx:
        saved = tx.one("SELECT count(*) AS n FROM app.planning_qualification_inbox")
        assert saved is not None and saved["n"] == 0


def test_scope_identity_cannot_transfer_between_tenants(database: Postgres) -> None:
    a, b, scope = str(uuid4()), str(uuid4()), "c" * 64
    inbox = QualificationInvalidations(database)
    inbox.accept(event(a, scope, 1))
    with pytest.raises(Rejected, match="invalidation_scope_conflict"):
        inbox.accept(event(b, scope, 2))


def test_same_tenant_unrelated_qualified_scope_is_not_withdrawn(database: Postgres) -> None:
    tenant = str(uuid4())
    first, second, unindexed = (add_plan(database, tenant) for _ in range(3))
    with database.transaction() as tx:
        for plan, scope in ((first, "a" * 64), (second, "b" * 64)):
            tx.execute(
                "INSERT INTO app.planning_plan_qualification_scopes"
                "(plan,tenant,scope_sha256) VALUES(%s,%s,%s)",
                (plan, tenant, scope),
            )

    QualificationInvalidations(database).accept(event(tenant, "a" * 64, 1))
    with database.transaction() as tx:
        counts = {
            plan: tx.one(
                "SELECT count(*) AS n FROM app.planning_invalidations WHERE plan=%s",
                (plan,),
            )
            for plan in (first, second, unindexed)
        }
    assert all(value is not None for value in counts.values())
    assert counts[first] is not None and counts[first]["n"] == 1
    assert counts[second] is not None and counts[second]["n"] == 0
    # Missing review-time scope remains fail-closed, never falsely unaffected.
    assert counts[unindexed] is not None and counts[unindexed]["n"] == 1
