import asyncio
import json
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from planning_fixture import ACTOR, APP, ENDPOINT, ENV, GENERATION, SITE, TENANT

from planning.domain.model import Actor, Rejected
from planning.interfaces.planning import PlanningApp

BASE = f"/v1/tenants/{TENANT}/applications/{APP}/environments/{ENV}"
CANDIDATE = {"site_id": SITE, "endpoint_id": ENDPOINT, "generation_id": GENERATION}


def exchange(
    app: PlanningApp,
    tail: str,
    body: bytes | None = None,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, dict[str, Any]]:
    sent: list[Any] = []

    async def run() -> None:
        scope: Any = {
            "type": "http",
            "path": BASE + tail,
            "method": "GET" if body is None else "POST",
            "query_string": b"",
            "headers": headers
            if headers is not None
            else [
                (b"authorization", b"Bearer " + b"a" * 64),
                (b"x-planning-delegations", (SITE + ":" + "b" * 64).encode()),
                (b"content-type", b"application/json"),
                (b"idempotency-key", str(uuid4()).encode()),
            ],
        }

        async def receive() -> Any:
            return {"type": "http.request", "body": body or b"", "more_body": False}

        async def send(message: Any) -> None:
            sent.append(message)

        await app(scope, receive, send)

    asyncio.run(run())
    assert (b"cache-control", b"no-store, private") in sent[0]["headers"]
    return sent[0]["status"], json.loads(sent[1]["body"])


def setup() -> tuple[PlanningApp, Any, Any]:
    planning, authority = Mock(), Mock()
    authority.actor.return_value = Actor(TENANT, ACTOR, "plan.read", APP, ENV)
    planning.get.return_value = {
        "candidates": [CANDIDATE],
        "content": {},
        "binding": {"digest": "a" * 64},
    }
    planning.validity.return_value = {"current": False}
    return PlanningApp(planning, authority), planning, authority


def test_revoked_actor_cannot_read_persisted_plan_or_current_sources() -> None:
    app, planning, authority = setup()
    authority.actor.side_effect = Rejected("access_denied", 403)
    assert exchange(app, "/plans/" + str(uuid4()))[0] == 403
    planning.validity.assert_not_called()


def test_hidden_diff_destination_requires_its_own_current_authority() -> None:
    app, planning, authority = setup()
    original = planning.get.return_value
    other = dict(original, candidates=[dict(CANDIDATE, site_id=str(uuid4()))])
    planning.get.side_effect = [original, other]
    authority.actor.side_effect = [
        Actor(TENANT, ACTOR, "plan.read", APP, ENV),
        Rejected("access_denied", 403),
    ]
    assert (
        exchange(
            app,
            "/plans/" + str(uuid4()) + "/diff",
            json.dumps({"other_plan_id": str(uuid4())}).encode(),
        )[0]
        == 403
    )
    assert authority.actor.call_count == 2


@pytest.mark.parametrize(
    "payload,expected",
    [
        (b"{" + b" " * 262144, 413),
        (b'{"candidates":[],"candidates":[]}', 422),
        (b'{"candidates":NaN}', 422),
    ],
)
def test_bounded_strict_request_precedes_source_reads(payload: bytes, expected: int) -> None:
    app, planning, _ = setup()
    assert exchange(app, "/assessments", payload)[0] == expected
    planning.assessment.assert_not_called()


def test_missing_workload_cannot_lookup_record() -> None:
    app, planning, _ = setup()
    assert exchange(app, "/plans/" + str(uuid4()), headers=[])[0] == 400
    planning.get.assert_not_called()


def test_two_sites_cannot_use_different_actors() -> None:
    app, _, authority = setup()
    authority.actor.side_effect = [
        Actor(TENANT, ACTOR, "plan.create", APP, ENV),
        Actor(TENANT, str(uuid4()), "plan.create", APP, ENV),
    ]
    with pytest.raises(Rejected, match="actor_mismatch"):
        app.authorize(
            "a" * 64,
            {},
            TENANT,
            "plan.create",
            APP,
            ENV,
            [CANDIDATE, dict(CANDIDATE, endpoint_id=str(uuid4()), site_id=str(uuid4()))],
        )
