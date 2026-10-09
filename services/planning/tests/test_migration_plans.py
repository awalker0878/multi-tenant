"""Complete immutable migration recipes stay bound to exact current owner inputs."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from test_migration_profiles import inputs, mapping
from test_planning_http import exchange

from planning.application.migration_plans import MigrationPlans
from planning.application.validation import MigrationValidation, PlanValidation
from planning.domain.migration import bind_migration
from planning.domain.migration_plan import DELTA, compose_migration, stage_order
from planning.domain.migration_api_selection import pin as pin_api_selection
from planning.domain.model import Actor, Rejected, digest
from planning.infrastructure.migration_recipes import recipe_for
from planning.interfaces.migration import MigrationPreparationApp


def values(
    mode: str = "cutover", method: str = "VM_COLD_EXPORT"
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    i = inputs()
    i["method"] = method
    i["objectives"] = {
        "owner_id": str(uuid4()),
        "acceptance_sha256": digest("objectives"),
        "max_outage_seconds": 3600,
        "max_data_loss_bytes": 0,
    }
    for side in ("source", "target"):
        i[side].update(
            {
                key: digest([side, key])
                for key in ("native_identity_sha256", "tuple_sha256", "profile_sha256")
            }
        )
    bound = bind_migration(i, mapping(), 1000)
    scope = {
        k: str(uuid4())
        for k in ("tenant_id", "site_id", "environment", "resource_id", "project_id")
    }
    base: dict[str, Any] = {
        "scope": {**scope, "native_scope": "project:" + scope["project_id"]},
        "action": "application.migrate",
        "lane": "operational",
        "execution_ready": True,
        "holds": [],
        "valid_until": 1200,
        "input_fresh_until": 1150,
        "ownership": [],
        "native_api": {"custody_id": str(uuid4()), "custody_generation": 1},
    }
    recipe = {
        "schema_version": 1,
        "scope": scope,
        "base_content_sha256": digest(base),
        "source_identity_sha256": bound["source"]["native_identity_sha256"],
        "target_identity_sha256": bound["target"]["native_identity_sha256"],
        "mode": mode,
        "method": method,
        "expires_at": 1300,
        "delta": {
            "kind": DELTA[method],
            "requires_running_guest": DELTA[method] in {"application", "file"},
            "qualification_sha256": digest("qualified"),
        },
        "artifacts": {
            k: digest(k)
            for k in ("capture", "transfer", "conversion", "guest", "delta", "recovery")
        },
        "rehearsal_sha256": digest("rehearsal") if mode == "cutover" else None,
        "recovery_of_sha256": digest("predecessor")
        if mode in {"rollback", "forward_recovery", "reverse_recovery", "cleanup"}
        else None,
        "source_job_id": str(uuid4())
        if mode in {"rollback", "forward_recovery", "reverse_recovery", "cleanup"}
        else None,
        "intents": {k: digest(k) for k in stage_order(mode, method)},
        "native": {
            "configuration": {"revision": 1, "digest": digest("config")},
            "tuple_digest": digest("tuple"),
            "source_revision": "a" * 40,
            "ownership_digest": digest(base["ownership"]),
            **base["native_api"],
            "policy_cases": [
                {
                    "id": b + "_" + e,
                    "boundary": b,
                    "expectation": e,
                    "family": "ipv4",
                    "direction": "forward",
                }
                for b in ("same_host_subnet", "inter_host", "edge")
                for e in ("allow", "deny")
            ],
        },
        "campaign": {
            "route_sha256": digest("route"),
            "sizes": {
                p: 1024
                for p in ("capture", "transfer", "conversion", "import", "validation", "cutover")
            },
            "demands": {"staging:site": 4096},
        },
    }
    return base, bound, recipe


def qualified_api_readiness(now: int = 1000) -> dict[str, Any]:
    return {
        "schema_version": 2, "kind": "migration_workload_readiness",
        "status": "eligible", "holds": [], "native_write_authorized": False,
        "expires_at": now + 100,
        "route_sha256": digest("route"), "release_sha256": digest("release"),
        "source": {"platform": "vmware", "profile_sha256": digest("src")},
        "target": {"platform": "openstack", "profile_sha256": digest("tgt")},
        "api_compatibility": {
            "operationally_eligible": True,
            "cases": [{
                "capability_id": "vm.disk.export", "side": "source",
                "criticality": "critical", "status": "eligible",
                "omission_accepted": False, "selected_api_family": "vmware.vi_json",
                "selected_api_version": "9.0.0.0",
                "evidence_sha256": digest("native-e3"),
                "expires_at": now + 100,
            }],
        },
    }


@pytest.mark.parametrize(
    "mode", ["rehearsal", "cutover", "rollback", "forward_recovery", "reverse_recovery", "cleanup"]
)
@pytest.mark.parametrize("method", list(DELTA))
def test_complete_plans_have_exact_order_and_preserve_owner_expiry(mode: str, method: str) -> None:
    base, bound, recipe = values(mode, method)
    before = deepcopy(base)
    result = compose_migration(base, bound, recipe, 1000)
    assert base == before
    assert result["valid_until"] == 1100
    assert [e["id"] for e in result["effects"]] == list(stage_order(mode, method))
    assert result["native_migration"]["migration"]["disks"] == bound["disks"]
    assert result["migration_campaign"]["method"] == method
    if mode == "rehearsal":
        assert "admit_writes" not in result["native_migration"]["intents"]


@pytest.mark.parametrize(
    "fault",
    [
        "source",
        "target",
        "site",
        "base",
        "method",
        "missing_stage",
        "duplicate_stage",
        "expired",
        "delta",
        "rehearsal",
        "recovery",
        "custody",
        "ownership",
        "policy",
        "data_budget",
        "unqualified",
    ],
)
def test_changed_or_incomplete_composition_cannot_create_operational_plan(fault: str) -> None:
    base, bound, recipe = values()
    if fault in {"source", "target"}:
        recipe[fault + "_identity_sha256"] = "f" * 64
    elif fault == "site":
        recipe["scope"]["site_id"] = str(uuid4())
    elif fault == "base":
        base["valid_until"] = 1101
    elif fault == "method":
        recipe["method"] = "VM_SNAPSHOT_BASELINE_FILE_DELTA"
    elif fault == "missing_stage":
        del recipe["intents"]["admit_writes"]
    elif fault == "duplicate_stage":
        recipe["intents"]["admit_writes"] = recipe["intents"]["capture"]
    elif fault == "expired":
        bound["source"]["expires_at"] = 1000
    elif fault == "delta":
        recipe["delta"]["requires_running_guest"] = True
    elif fault == "rehearsal":
        recipe["rehearsal_sha256"] = None
    elif fault == "recovery":
        recipe["source_job_id"] = str(uuid4())
    elif fault == "custody":
        recipe["native"]["custody_generation"] += 1
    elif fault == "ownership":
        recipe["native"]["ownership_digest"] = "f" * 64
    elif fault == "policy":
        recipe["native"]["policy_cases"] = recipe["native"]["policy_cases"][:5]
    elif fault == "data_budget":
        recipe["campaign"]["sizes"]["transfer"] = 1023
    else:
        base["execution_ready"] = False
        recipe["base_content_sha256"] = digest(base)
    with pytest.raises(Rejected):
        compose_migration(base, bound, recipe, 1000)


def test_recipe_lookup_is_tenant_application_environment_site_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, recipe = values()
    scope = recipe["scope"]
    actor = Actor(
        scope["tenant_id"], str(uuid4()), "plan.create", scope["resource_id"], scope["environment"]
    )
    path = tmp_path / "recipes.json"
    key = str(uuid4())
    path.write_text(json.dumps({"schema_version": 1, "recipes": [{"id": key, "recipe": recipe}]}))
    monkeypatch.setenv("PLANNING_MIGRATION_RECIPES_FILE", str(path))
    assert recipe_for(actor, scope["site_id"], key) == recipe
    with pytest.raises(Rejected, match="unavailable"):
        recipe_for(actor, str(uuid4()), key)
    path.chmod(0o666)
    with pytest.raises(Rejected, match="unavailable"):
        recipe_for(actor, scope["site_id"], key)


def test_complete_plan_http_requires_idempotency_and_authority_before_compile() -> None:
    from planning_fixture import SITE

    authority, service = Mock(), Mock()
    service.create.return_value = {"native_write_authorized": False, "id": str(uuid4())}
    app: Any = MigrationPreparationApp(authority, Mock(), service)
    body = {
        "site_id": SITE,
        "review": {"revision": 1, "digest": digest("review")},
        "disks": mapping(),
        "recipe_id": str(uuid4()),
        "base_plan_id": str(uuid4()),
    }
    headers = [
        (b"authorization", b"Bearer " + b"a" * 64),
        (b"content-type", b"application/json"),
        (b"x-actor-delegation", b"b" * 64),
    ]
    assert exchange(app, "/migration-plans", json.dumps(body).encode(), headers)[0] == 400
    service.create.assert_not_called()
    status, result = exchange(
        app,
        "/migration-plans",
        json.dumps(body).encode(),
        headers + [(b"idempotency-key", str(uuid4()).encode())],
    )
    assert status == 201 and result["native_write_authorized"] is False
    service.create.reset_mock()
    authority.actor.side_effect = Rejected("denied", 403)
    assert exchange(app, "/migration-plans", json.dumps(body).encode(), headers)[0] == 403
    service.create.assert_not_called()


def test_plan_revalidation_observes_recipe_revocation_and_inventory_changes() -> None:
    base, bound, recipe = values()
    planner = Mock()
    planner.clock.return_value = 1000
    prepare, recipes = Mock(return_value=bound), Mock(return_value=recipe)
    validation = MigrationValidation(
        prepare, recipes, Mock(return_value=qualified_api_readiness()), planner.clock
    )
    planner.validation.migration = validation
    service = MigrationPlans(planner, validation)
    content = compose_migration(base, bound, recipe, 1000)
    actor = Actor(
        recipe["scope"]["tenant_id"],
        str(uuid4()),
        "plan.read",
        recipe["scope"]["resource_id"],
        recipe["scope"]["environment"],
    )
    content["native_migration"]["api_selection"] = pin_api_selection(
        qualified_api_readiness(), 1000
    )
    content["native_migration"]["recipe_id"] = str(uuid4())
    plan = {"content": content}
    service.current(actor, plan, {recipe["scope"]["site_id"]: "delegation"})
    assert prepare.call_args.kwargs == {"action": "plan.read"}
    prepare.return_value = bound | {"owner_inputs_sha256": "e" * 64}
    with pytest.raises(Rejected, match="profiles_changed"):
        service.current(actor, plan, {})
    recipes.return_value = recipe | {"expires_at": 999}
    with pytest.raises(Rejected, match="recipe_changed"):
        service.current(actor, plan, {})


def test_complete_plan_options_persistence_retry_and_wire_schema(database: Any) -> None:
    from jsonschema import Draft202012Validator, FormatChecker
    from planning_fixture import APP, ENV, NOW, SITE, TENANT, request
    from test_planning_store import Sources, setup

    planner, actor, assessment_body = setup(database)
    assert isinstance(planner.sources, Sources)
    qualification = planner.sources.value["inputs"][0]["qualification"]
    qualification["scope"].update(action="application.migrate", method="native_api_export_import")
    from planning_fixture import verify_fixture

    verify_fixture(qualification)
    destination = planner.sources.value["inputs"][0]["destination"]
    destination["capability_snapshot"]["scope_sha256"] = digest(qualification["scope"])
    assessment_body.update(action="application.migrate", method="native_api_export_import")
    assessment_receipt = planner.assessment(actor, str(uuid4()), assessment_body, {})
    assessed = planner.get(TENANT, APP, ENV, assessment_receipt["id"], "assessment")
    request_body = request() | {
        "action": "application.migrate",
        "method": "native_api_export_import",
    }
    base_receipt = planner.plan(
        actor,
        str(uuid4()),
        {"assessment_id": assessed["id"], "candidate": 0, "request": request_body},
        assessed,
    )
    base = planner.get(TENANT, APP, ENV, base_receipt["id"], "plan")
    assert base["content"]["execution_ready"] is True
    _, bound, recipe = values()
    for side in ("source", "target"):
        bound[side].update(observed_at=NOW - 10, expires_at=NOW + 100)
    content = base["content"]
    recipe.update(
        scope={
            k: content["scope"][k] for k in ("tenant_id", "site_id", "resource_id", "environment")
        }
        | {"project_id": content["scope"]["native_scope"].split(":")[1]},
        base_content_sha256=digest(content),
        expires_at=NOW + 100,
    )
    recipe["native"].update(
        ownership_digest=digest(content["ownership"]),
        custody_id=content["native_api"]["custody_id"],
        custody_generation=content["native_api"]["custody_generation"],
    )
    recipe_id, key = str(uuid4()), str(uuid4())
    prepare = Mock(return_value=bound)
    recipes = Mock(return_value=recipe)
    from planning.application.planning import Planning

    validation = MigrationValidation(
        prepare, recipes, Mock(return_value=qualified_api_readiness()), planner.clock
    )
    planner = Planning(
        planner.database,
        planner.sources,
        planner.clock,
        PlanValidation(planner.validation.native, validation, Mock()),
    )
    service = MigrationPlans(
        planner, validation, lambda a, s: [{"id": recipe_id, "recipe": recipe}]
    )
    body = {
        "site_id": SITE,
        "review": bound["review"],
        "disks": [
            {k: d[k] for k in ("source_disk_sha256", "target_key", "format")}
            for d in bound["disks"]
        ],
    }
    options = service.options(actor, body, "delegation")
    assert options["items"][0]["base_plan_id"] == base["id"]
    body.update(base_plan_id=base["id"], recipe_id=recipe_id)
    receipt = service.create(actor, body, key, "delegation")
    saved = planner.get(TENANT, APP, ENV, receipt["id"], "plan")
    assert saved["binding"]["digest"] != base["binding"]["digest"]
    assert saved["content"]["native_migration"]["base_plan_id"] == base["id"]
    assert receipt["native_write_authorized"] is False
    validity = planner.validity(actor, saved, {SITE: "delegation"})
    assert validity["current"] is True
    spec = json.loads((Path(__file__).with_name("fixtures") / "planning-v1.1.json").read_text())
    Draft202012Validator(
        {"$ref": "#/components/schemas/Plan", "components": spec["components"]},
        format_checker=FormatChecker(),
    ).validate(saved | {"validity": validity})
    # Exact retry resolves durable state even after input owners disappear.
    prepare.side_effect = Rejected("unavailable", 503)
    recipes.side_effect = Rejected("unavailable", 503)
    assert service.create(actor, body, key, "delegation") == receipt
    with pytest.raises(Rejected, match="command_key_conflict"):
        service.create(actor, body | {"recipe_id": str(uuid4())}, key, "delegation")
    with database.transaction() as tx:
        assert tx.one("SELECT count(*) AS n FROM app.planning_records WHERE kind='plan'")["n"] == 2
        assert tx.one("SELECT count(*) AS n FROM app.planning_outbox")["n"] == 3


def test_unattended_execution_and_governance_reads_recheck_recipe_revocation() -> None:
    from unittest.mock import MagicMock

    from planning.application.planning import Planning

    base, bound, recipe = values()
    content = compose_migration(base, bound, recipe, 1000)
    content["native_migration"].update(recipe_id=str(uuid4()), base_plan_id=str(uuid4()))
    content["native_migration"]["api_selection"] = pin_api_selection(
        qualified_api_readiness(), 1000
    )
    payload = {"content": content, "binding": {"requested_by": str(uuid4())}}
    database = MagicMock()
    tx = database.transaction.return_value.__enter__.return_value
    recipes = Mock(return_value=recipe)

    def clock() -> int:
        return 1000

    denied = Planning(database, Mock(), clock, PlanValidation.unavailable(clock))
    validation = PlanValidation.unavailable(clock)
    validation = PlanValidation(
        validation.native, MigrationValidation(
            Mock(), recipes,
            Mock(return_value=qualified_api_readiness()), clock,
        ), Mock()
    )
    planning = Planning(database, Mock(), clock, validation)
    key, tenant = str(uuid4()), recipe["scope"]["tenant_id"]
    tx.one.side_effect = [{"payload": payload}]
    with pytest.raises(Rejected, match="validation_authority"):
        denied.execution_plan(tenant, key, 1)
    tx.one.side_effect = [{"payload": payload}, None, {"payload": payload}]
    assert planning.execution_plan(tenant, key, 1)["invalidated"] is False
    assert planning.bound_plan(key, 1) == payload["binding"]
    assert recipes.call_count == 2
    recipes.return_value = recipe | {"expires_at": 999}
    for native in (True, False):
        tx.one.side_effect = [{"payload": payload}]
        with pytest.raises(Rejected, match="recipe_changed"):
            if native:
                planning.execution_plan(tenant, key, 1)
            else:
                planning.bound_plan(key, 1)


def test_ahv_recipe_binds_exact_reviewed_destination_devices() -> None:
    base, bound, recipe = values()
    bound["destination_sha256"] = digest({"cluster": "observed", "quarantine": "selected"})
    recipe.update(schema_version=2, destination_sha256=bound["destination_sha256"])
    base["native_api"]["operation_plan"] = {
        "kind": "ahv_destination",
        "destination_sha256": bound["destination_sha256"],
    }
    recipe["base_content_sha256"] = digest(base)
    recipe["intents"]["import_target"] = digest(base["native_api"]["operation_plan"])
    result = compose_migration(base, bound, recipe, 1000)
    assert result["native_migration"]["migration"]["schema_version"] == 3
    assert (
        result["native_migration"]["migration"]["destination_sha256"] == bound["destination_sha256"]
    )
    recipe["destination_sha256"] = digest("different NIC mapping")
    with pytest.raises(Rejected, match="destination_mapping_changed"):
        compose_migration(base, bound, recipe, 1000)
