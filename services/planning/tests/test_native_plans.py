"""P07 proposals cannot replace an approved API plan, scope or independent policy matrix."""

import json
from copy import deepcopy
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from test_migration_plans import values
from test_planning_http import exchange

from planning.application.native_plans import NativePlans
from planning.application.planning import Planning
from planning.application.validation import NativeValidation, PlanValidation
from planning.domain.model import Rejected, digest
from planning.domain.native_plan import STAGES, compose_native
from planning.interfaces.native_plans import NativePlansApp


def native_values(purpose: str = "provision") -> tuple[dict[str, Any], dict[str, Any]]:
    base, _, migration = values()
    base["action"] = "application." + purpose
    base["native_api"]["operation_plan_sha256"] = digest(purpose)
    recipe = {
        "schema_version": 1,
        "scope": migration["scope"],
        "base_content_sha256": digest(base),
        "purpose": purpose,
        "source_job_id": str(uuid4()) if purpose == "retire" else None,
        "expires_at": 1400,
        "native": migration["native"],
        "intents": {s: digest(s) for s in STAGES[purpose]},
    }
    return base, recipe


@pytest.mark.parametrize("purpose", ["provision", "retire"])
def test_complete_proposal_preserves_qualified_scope_artifacts_and_expiry(purpose: str) -> None:
    base, recipe = native_values(purpose)
    original = deepcopy(base)
    content = compose_native(base, recipe, 1000)
    assert base == original
    assert content["valid_until"] == 1150
    assert content["native_provisioning"]["native"] == recipe["native"]
    assert (
        content["native_provisioning"]["intents"][purpose]
        == base["native_api"]["operation_plan_sha256"]
    )
    assert content["effects"][-1]["id"] == ("activate" if purpose == "provision" else "release")
    assert "native_write_authorized" not in content


@pytest.mark.parametrize(
    "fault",
    [
        "scope",
        "project",
        "base",
        "api",
        "purpose",
        "missing_stage",
        "stage_reuse",
        "custody",
        "policy",
        "expired",
        "source_job",
        "held",
    ],
)
def test_incomplete_changed_or_unqualified_native_proposals_are_denied(fault: str) -> None:
    base, recipe = native_values()
    if fault == "scope":
        recipe["scope"]["site_id"] = str(uuid4())
    elif fault == "project":
        recipe["scope"]["project_id"] = str(uuid4())
    elif fault == "base":
        recipe["base_content_sha256"] = "b" * 64
    elif fault == "api":
        recipe["intents"]["provision"] = "f" * 64
    elif fault == "purpose":
        recipe["purpose"] = "migrate"
    elif fault == "missing_stage":
        del recipe["intents"]["enroll_services"]
    elif fault == "stage_reuse":
        recipe["intents"]["activate"] = recipe["intents"]["reserve"]
    elif fault == "custody":
        recipe["native"]["custody_generation"] += 1
    elif fault == "policy":
        recipe["native"]["policy_cases"][-1]["expectation"] = "allow"
    elif fault == "expired":
        recipe["expires_at"] = 1000
    elif fault == "source_job":
        recipe["source_job_id"] = str(uuid4())
    else:
        base["holds"] = ["provider_unqualified"]
        recipe["base_content_sha256"] = digest(base)
    with pytest.raises(Rejected):
        compose_native(base, recipe, 1000)


def test_unattended_recipe_revocation_is_checked_without_user_delegation() -> None:
    base, recipe = native_values()
    content = compose_native(base, recipe, 1000)
    content["native_provisioning"]["recipe_id"] = str(uuid4())
    planning, source = Mock(spec=Planning), Mock(return_value=recipe)
    planning.clock = lambda: 1000
    validation = NativeValidation(source, planning.clock)
    planning.validation.native = validation
    service = NativePlans(planning, validation)
    plan = {"content": content, "binding": {"requested_by": str(uuid4())}}
    service.current(plan)
    recipe["expires_at"] = 999
    with pytest.raises(Rejected, match="native_recipe_changed"):
        service.current(plan)


def test_native_http_requires_actor_before_composing_and_rejects_inline_intents() -> None:
    authority, plans = Mock(), Mock(spec=NativePlans)
    app: Any = NativePlansApp(authority, plans)
    headers = [
        (b"authorization", b"Bearer " + b"a" * 64),
        (b"x-actor-delegation", b"b" * 64),
        (b"content-type", b"application/json"),
        (b"idempotency-key", str(uuid4()).encode()),
    ]
    body = {k: str(uuid4()) for k in ("site_id", "base_plan_id", "recipe_id")}
    plans.create.return_value = {"id": str(uuid4())}
    assert exchange(app, "/native-plans", json.dumps(body).encode(), headers)[0] == 201
    authority.actor.side_effect = Rejected("denied", 403)
    plans.create.reset_mock()
    assert exchange(app, "/native-plans", json.dumps(body).encode(), headers)[0] == 403
    plans.create.assert_not_called()
    body["intents"] = "injected"
    assert exchange(app, "/native-plans", json.dumps(body).encode(), headers)[0] == 422


def test_complete_native_proposal_persistence_retry_and_revocation(database: Any) -> None:
    from planning_fixture import APP, ENV, NOW, SITE, TENANT, request
    from test_planning_store import setup

    planner, actor, assessment_body = setup(database)
    assessed_id = planner.assessment(actor, str(uuid4()), assessment_body, {})["id"]
    assessed = planner.get(TENANT, APP, ENV, assessed_id, "assessment")
    base_id = planner.plan(
        actor,
        str(uuid4()),
        {"assessment_id": assessed_id, "candidate": 0, "request": request()},
        assessed,
    )["id"]
    base = planner.get(TENANT, APP, ENV, base_id, "plan")["content"]
    _, recipe = native_values()
    recipe.update(
        scope={k: base["scope"][k] for k in ("tenant_id", "site_id", "resource_id", "environment")}
        | {"project_id": base["scope"]["native_scope"].split(":")[1]},
        base_content_sha256=digest(base),
        expires_at=NOW + 100,
    )
    recipe["intents"]["provision"] = base["native_api"]["operation_plan_sha256"]
    recipe["native"].update(
        ownership_digest=digest(base["ownership"]),
        custody_id=base["native_api"]["custody_id"],
        custody_generation=base["native_api"]["custody_generation"],
    )
    source = Mock(return_value=recipe)
    from planning.application.planning import Planning

    validation = NativeValidation(source, planner.clock)
    planner = Planning(
        planner.database,
        planner.sources,
        planner.clock,
        PlanValidation(validation, planner.validation.migration),
    )
    service = NativePlans(planner, validation)
    body = {"site_id": SITE, "base_plan_id": base_id, "recipe_id": str(uuid4())}
    key = str(uuid4())
    receipt = service.create(actor, body, key, "delegation")
    saved = planner.get(TENANT, APP, ENV, receipt["id"], "plan")
    assert saved["binding"]["content_digest"] == digest(saved["content"])
    assert receipt["native_write_authorized"] is False
    assert planner.validity(actor, saved, {SITE: "delegation"})["current"] is True
    source.side_effect = Rejected("recipe_revoked", 423)
    assert planner.validity(actor, saved, {SITE: "delegation"})["current"] is False
    assert service.create(actor, body, key, "delegation") == receipt
    with pytest.raises(Rejected, match="command_key_conflict"):
        service.create(actor, body | {"recipe_id": str(uuid4())}, key, "delegation")
    with database.transaction() as tx:
        assert tx.one("SELECT count(*) AS n FROM app.planning_records WHERE kind='plan'")["n"] == 2
