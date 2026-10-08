from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from planning_fixture import (
    ACTOR,
    APP,
    ENDPOINT,
    ENV,
    GENERATION,
    NOW,
    REVISION,
    SITE,
    TENANT,
    assessment,
    request,
)

from planning.application.planning import Planning
from planning.application.qualification_invalidations import QualificationInvalidations
from planning.application.validation import PlanValidation
from planning.domain.model import Actor, Rejected, digest
from planning.infrastructure.store import Postgres


class Sources:
    def __init__(self) -> None:
        self.value = assessment()

    def resolve(
        self,
        actor: Actor,
        revision: str,
        candidates: list[dict[str, Any]],
        delegations: dict[str, str],
        action: str,
        method: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        return deepcopy(self.value["intent"]), deepcopy(self.value["inputs"])


def setup(database: Postgres) -> tuple[Planning, Actor, dict[str, Any]]:
    return (
        Planning(database, Sources(), lambda: NOW, PlanValidation.unavailable(lambda: NOW)),
        Actor(TENANT, ACTOR, "plan.create", APP, ENV),
        {
            "revision_id": REVISION,
            "action": "application.provision",
            "method": "native_api",
            "candidates": [{"site_id": SITE, "endpoint_id": ENDPOINT, "generation_id": GENERATION}],
        },
    )


def test_atomic_retry_race_and_restart(database: Postgres) -> None:
    p, a, b = setup(database)
    key = str(uuid4())
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda _: p.assessment(a, key, b, {}), range(2)))
    assert replies[0] == replies[1]
    second = Planning(
        database, Sources(), lambda: NOW + 2, PlanValidation.unavailable(lambda: NOW + 2)
    )
    assert second.assessment(a, key, b, {}) == replies[0]
    with database.transaction() as tx:
        records = tx.one("SELECT count(*) AS n FROM app.planning_records")
        assert records is not None and records["n"] == 1
        outbox = tx.one("SELECT count(*) AS n FROM app.planning_outbox")
        assert outbox is not None and outbox["n"] == 1
    with pytest.raises(Rejected, match="command_key_conflict"):
        p.assessment(a, key, dict(b, method="native_api_export_import"), {})


def test_immutable_history_and_tenant_isolation(database: Postgres) -> None:
    p, a, b = setup(database)
    r = p.assessment(a, str(uuid4()), b, {})
    with pytest.raises(Rejected, match="not_found"):
        p.get(str(uuid4()), APP, ENV, r["id"], "assessment")
    with pytest.raises(psycopg.errors.InsufficientPrivilege), database.transaction() as tx:
        tx.execute("UPDATE app.planning_records SET digest=%s", ("a" * 64,))
    with pytest.raises(psycopg.errors.InsufficientPrivilege), database.transaction() as tx:
        tx.execute("DELETE FROM app.planning_records")


def test_plan_persistence_invalidation_duplicate_and_conflict(database: Postgres) -> None:
    p, a, b = setup(database)
    r = p.assessment(a, str(uuid4()), b, {})
    assessed = p.get(TENANT, APP, ENV, r["id"], "assessment")
    plan = p.plan(
        a, str(uuid4()), {"assessment_id": r["id"], "candidate": 0, "request": request()}, assessed
    )
    saved = p.get(TENANT, APP, ENV, plan["id"], "plan")
    with database.transaction() as tx:
        index = tx.one(
            "SELECT scope_sha256 FROM app.planning_plan_qualification_scopes WHERE plan=%s",
            (plan["id"],),
        )
    assert index is not None
    assert index["scope_sha256"] == digest(
        assessed["inputs"][0]["qualification"]["scope"]
    )
    assert p.validity(a, saved, {})["current"]
    event = {
        "event_id": str(uuid4()),
        "tenant_id": TENANT,
        "event_type": "inventory.discovery.completed",
        "sequence": 1,
    }
    assert p.invalidate(event)
    assert not p.invalidate(event)
    assert not p.validity(a, saved, {})["current"]
    assert p.get(TENANT, APP, ENV, plan["id"], "plan") == saved
    with pytest.raises(Rejected, match="event_id_conflict"):
        p.invalidate(dict(event, sequence=2))


def test_expiry_and_unavailable_inputs_preserve_plan(database: Postgres) -> None:
    p, a, b = setup(database)
    r = p.assessment(a, str(uuid4()), b, {})
    assessed = p.get(TENANT, APP, ENV, r["id"], "assessment")
    r = p.plan(
        a, str(uuid4()), {"assessment_id": r["id"], "candidate": 0, "request": request()}, assessed
    )
    saved = p.get(TENANT, APP, ENV, r["id"], "plan")
    p.clock = lambda: NOW + 5000
    assert "plan_or_facts_expired" in p.validity(a, saved, {})["holds"]
    assert p.get(TENANT, APP, ENV, r["id"], "plan") == saved


def test_negative_qualification_arriving_before_plan_save_cannot_be_missed(
    database: Postgres,
) -> None:
    p, actor, body = setup(database)
    result = p.assessment(actor, str(uuid4()), body, {})
    assessed = p.get(TENANT, APP, ENV, result["id"], "assessment")
    scope_sha256 = digest(assessed["inputs"][0]["qualification"]["scope"])
    incoming = {
        "event_id": str(uuid4()),
        "tenant_id": TENANT,
        "scope_sha256": scope_sha256,
        "authority_epoch": 1,
        "operation": "revoke",
        "state": "revoked",
        "decision_sha256": "a" * 64,
        "event_sha256": "b" * 64,
    }
    QualificationInvalidations(database).accept(incoming)

    planned = p.plan(
        actor,
        str(uuid4()),
        {"assessment_id": result["id"], "candidate": 0, "request": request()},
        assessed,
    )
    with database.transaction() as tx:
        holds = tx.one(
            "SELECT count(*) AS n FROM app.planning_invalidations WHERE plan=%s",
            (planned["id"],),
        )
    assert holds is not None and holds["n"] == 1
    saved = p.get(TENANT, APP, ENV, planned["id"], "plan")
    assert not p.validity(actor, saved, {})["current"]
