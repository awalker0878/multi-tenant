"""Native control with real owner-separated PostgreSQL and synthetic owner observations."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from typing import Any
from uuid import uuid4

import psycopg
import pytest

from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.domain.native_workflow import (
    AFTER,
    BEFORE,
    PROVISION,
    RETIRE,
    current_authority,
    observations,
    validate_plan,
)


def plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "scope": {
            k: str(uuid4())
            for k in ("tenant_id", "site_id", "environment", "resource_id", "project_id")
        },
        **{
            k: str(uuid4())
            for k in (
                "plan_id",
                "approval_id",
                "actor_id",
                "requester_id",
                "approver_id",
                "executor_id",
                "campaign_id",
                "epoch",
                "state_lineage",
            )
        },
        "plan_revision": 1,
        "plan_digest": "a" * 64,
        "configuration": {"revision": 1, "digest": "c" * 64},
        "tuple_digest": "d" * 64,
        "source_revision": "e" * 40,
        "purpose": "provision",
        "source_job_id": None,
        "workspace": "default",
        "state_serial": 1,
        "bundle_sha256": "f" * 64,
        "expires_at": 2000,
        "intents": {s: digest(s) for s in PROVISION},
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
    }


class Owners:
    def __init__(self, document: dict[str, Any]) -> None:
        self.document = document
        self.now = 1000
        self.current_epoch = document["epoch"]
        self.observer = str(uuid4())
        self.authority_changes: dict[str, Any] = {}
        self.evidence_changes: dict[str, Any] = {}
        self.omit: str | None = None
        self.failure = False
        self.epoch_reads = 0
        self.change_epoch_after = 0

    def epoch(self) -> str:
        self.epoch_reads += 1
        if self.change_epoch_after and self.epoch_reads >= self.change_epoch_after:
            return str(uuid4())
        return str(self.current_epoch)

    def current(self, p: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
        return {
            "binding_sha256": digest(binding),
            "plan_digest": p["plan_digest"],
            "configuration": p["configuration"],
            "tuple_digest": p["tuple_digest"],
            "epoch": p["epoch"],
            "executor_id": p["executor_id"],
            "authority_use": "native_boundary",
            "allowed": True,
            "native_write_authorized": True,
            "stop_clear": True,
            "configuration_current": True,
            "approval_current": True,
            "ownership_current": True,
            "provider_fence_current": True,
            "plan_current": True,
            "state_current": True,
            "artifacts_current": True,
            "entitlement_current": True,
            "campaign_current": True,
            "evaluated_at": self.now,
            "expires_at": p["expires_at"],
            **self.authority_changes,
        }

    def observe(
        self, p: dict[str, Any], binding: dict[str, Any], phase: str
    ) -> list[dict[str, Any]]:
        if self.failure:
            raise OSError("synthetic_private_provider_message")
        required = BEFORE[binding["stage"]] if phase == "before" else AFTER[binding["stage"]]
        return [
            {
                "case": case,
                "phase": phase,
                "binding_sha256": digest(binding),
                "intent_digest": p["intents"][binding["stage"]],
                "observer_id": self.observer,
                "observed_at": self.now,
                "expires_at": self.now + 30,
                "outcome": "passed",
                "evidence_sha256": digest([case, binding]),
                "policy_results": {c["id"]: c["expectation"] for c in p["policy_cases"]}
                if case == "policy_paths"
                else {},
                **self.evidence_changes,
            }
            for case in required
            if case != self.omit
        ]


@pytest.fixture()
def native(
    database: Any, postgres: dict[str, Any]
) -> tuple[NativeWorkflow, Owners, dict[str, Any]]:
    p = plan()
    with psycopg.connect(**postgres) as c:
        c.execute("INSERT INTO app.native_control VALUES(1,%s,false)", (p["epoch"],))
    owners = Owners(p)
    return NativeWorkflow(database, owners, lambda: owners.now), owners, p


def admitted(
    native: tuple[NativeWorkflow, Owners, dict[str, Any]],
) -> tuple[NativeWorkflow, Owners, dict[str, Any], str, str]:
    service, owners, p = native
    tenant = p["scope"]["tenant_id"]
    job = service.admit(p, str(uuid4()))
    return service, owners, p, tenant, job


def complete(
    service: NativeWorkflow, p: dict[str, Any], tenant: str, job: str, stage: str
) -> dict[str, Any]:
    bound = service.prepare(tenant, job, stage)
    service.boundary(tenant, bound, p["executor_id"], "preflight")
    boundary = "before_saved_plan_apply" if stage == "provision" else "before_effect"
    service.boundary(tenant, bound, p["executor_id"], boundary)
    service.boundary(tenant, bound, p["executor_id"], boundary.replace("before", "during"))
    service.reconcile(tenant, bound)
    return bound


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("state_serial", True),
        ("expires_at", 1000),
        ("source_revision", "unbound"),
        ("workspace", "../other"),
        ("intents", {}),
        ("policy_cases", []),
        ("purpose", "destroy"),
    ],
)
def test_malformed_or_incomplete_plan(field: str, value: Any) -> None:
    p = plan()
    p[field] = value
    with pytest.raises(Rejected):
        validate_plan(p, 1000)


@pytest.mark.parametrize(
    "field,value",
    [
        ("native_write_authorized", False),
        ("allowed", 1),
        ("stop_clear", False),
        ("configuration_current", False),
        ("approval_current", False),
        ("ownership_current", False),
        ("plan_current", False),
        ("state_current", False),
        ("artifacts_current", False),
        ("entitlement_current", False),
        ("campaign_current", False),
        ("provider_fence_current", False),
        ("authority_use", "simulation_boundary"),
        ("epoch", str(uuid4())),
        ("configuration", {"revision": 2, "digest": "c" * 64}),
        ("evaluated_at", 994),
        ("evaluated_at", 1001),
        ("expires_at", 1000),
        ("binding_sha256", "f" * 64),
    ],
)
def test_current_authority_rejects_drift_and_simulation(field: str, value: Any) -> None:
    p = plan()
    owner = Owners(p)
    receipt = owner.current(p, {}) | {field: value}
    with pytest.raises(Rejected):
        current_authority(p, {}, receipt, 1000)


@pytest.mark.parametrize("case", BEFORE["activate"])
def test_activation_requires_each_service_restore_application_and_policy_case(case: str) -> None:
    p = plan()
    owner = Owners(p)
    owner.omit = case
    binding = {"stage": "activate"}
    with pytest.raises(Rejected, match="incomplete"):
        observations(p, binding, "before", owner.observe(p, binding, "before"), 1000)


@pytest.mark.parametrize(
    "changes",
    [
        {"phase": "after"},
        {"observer_id": "SELF"},
        {"outcome": "unknown"},
        {"observed_at": 1001},
        {"observed_at": 939},
        {"expires_at": 1000},
        {"intent_digest": "0" * 64},
        {"binding_sha256": "0" * 64},
    ],
)
def test_independent_observation_scope_and_time(changes: dict[str, Any]) -> None:
    p = plan()
    owner = Owners(p)
    owner.evidence_changes = changes.copy()
    if changes.get("observer_id") == "SELF":
        owner.evidence_changes["observer_id"] = p["executor_id"]
    binding = {"stage": "reserve"}
    with pytest.raises(Rejected):
        observations(p, binding, "before", owner.observe(p, binding, "before"), 1000)


def test_policy_matrix_covers_denied_paths_and_exact_results() -> None:
    p = plan()
    missing = deepcopy(p)
    missing["policy_cases"][-1]["expectation"] = "allow"
    with pytest.raises(Rejected, match="coverage"):
        validate_plan(missing, 1000)
    bound = {"stage": "activate"}
    records = Owners(p).observe(p, bound, "before")
    policy = next(r for r in records if r["case"] == "policy_paths")
    policy["policy_results"]["edge_deny"] = "allow"
    with pytest.raises(Rejected, match="policy_not_observed"):
        observations(p, bound, "before", records, 1000)


def test_whole_journey_and_separately_authorized_retirement(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    first = None
    for stage in PROVISION:
        result = complete(service, p, tenant, job, stage)
        first = first or result
    assert service.read(tenant, job)["state"] == "active"
    assert first is not None
    assert service.reconcile(tenant, first) == "active"  # old result cannot regress projection
    retirement = deepcopy(p)
    retirement.update(
        purpose="retire",
        source_job_id=job,
        intents={s: digest(s) for s in RETIRE},
        plan_id=str(uuid4()),
        plan_digest="b" * 64,
        approval_id=str(uuid4()),
    )
    second = service.admit(retirement, str(uuid4()))
    for stage in RETIRE:
        complete(service, retirement, tenant, second, stage)
    read = service.read(tenant, second)
    assert read["state"] == "retired" and read["retry_authorized"] is False
    assert read["native_qualification"] == "not_established"
    with pytest.raises(Rejected, match="held"):
        service.admit(p, str(uuid4()))


def test_concurrent_admission_and_grant_redemption_are_once(native: Any) -> None:
    service, owners, p = native
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = list(pool.map(lambda _: service.admit(p, key), range(8)))
    assert len(set(jobs)) == 1
    tenant, job = p["scope"]["tenant_id"], jobs[0]
    binding = service.prepare(tenant, job, "reserve")

    def redeem(_: int) -> str:
        try:
            service.boundary(tenant, binding, p["executor_id"], "before_effect")
            return "accepted"
        except Rejected as error:
            return error.reason

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(redeem, range(8)))
    assert results.count("accepted") == 1
    assert results.count("native_grant_already_redeemed") == 7
    fresh = NativeWorkflow(service.database, owners, lambda: owners.now)
    with pytest.raises(Rejected, match="reconciliation"):
        fresh.prepare(tenant, job, "reserve")


def test_stale_command_cross_tenant_and_cross_worker_denied(native: Any) -> None:
    service, owners, p = native
    key = str(uuid4())
    job = service.admit(p, key)
    changed = deepcopy(p)
    changed["configuration"]["revision"] = 2
    with pytest.raises(Rejected, match="conflict"):
        service.admit(changed, key)
    tenant = p["scope"]["tenant_id"]
    binding = service.prepare(tenant, job, "reserve")
    with pytest.raises(Rejected, match="not_found"):
        service.boundary(str(uuid4()), binding, p["executor_id"], "before_effect")
    with pytest.raises(Rejected, match="binding_denied"):
        service.boundary(tenant, binding, str(uuid4()), "before_effect")
    with pytest.raises(Rejected, match="boundary_mismatch"):
        service.boundary(tenant, binding, p["executor_id"], "before_saved_plan_apply")
    altered = binding | {"intent_digest": "0" * 64}
    with pytest.raises(Rejected, match="binding_denied"):
        service.reconcile(tenant, altered)
    assert service.read(tenant, job)["state"] == "running"


def test_unknown_outcome_retains_hold_until_complete_quiescent_readback(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    b = service.prepare(tenant, job, "reserve")
    service.boundary(tenant, b, p["executor_id"], "before_effect")
    owners.omit = "provider_requests_quiescent"
    with pytest.raises(Rejected, match="reconciliation"):
        service.reconcile(tenant, b)
    assert service.read(tenant, job)["state"] == "held"
    with pytest.raises(Rejected, match="held"):
        service.prepare(tenant, job, "provision")
    owners.omit = None
    assert service.reconcile(tenant, b) == "running"
    with pytest.raises(Rejected, match="reconciliation"):
        service.prepare(tenant, job, "reserve")
    complete(service, p, tenant, job, "provision")


def test_stop_is_terminal_for_writes_even_after_successful_readback(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    b = service.prepare(tenant, job, "reserve")
    service.boundary(tenant, b, p["executor_id"], "before_effect")
    service.stop(tenant, job)
    with pytest.raises(Rejected, match="held"):
        service.boundary(tenant, b, p["executor_id"], "during_effect")
    assert service.reconcile(tenant, b) == "stopped"
    with pytest.raises(Rejected, match="held"):
        service.prepare(tenant, job, "provision")


def test_epoch_rotation_or_restored_old_database_never_reopens_authority(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    b = service.prepare(tenant, job, "reserve")
    owners.current_epoch = str(uuid4())
    with pytest.raises(Rejected, match="custody"):
        service.boundary(tenant, b, p["executor_id"], "before_effect")
    owners.current_epoch = p["epoch"]
    owners.change_epoch_after = owners.epoch_reads + 2
    with pytest.raises(Rejected, match="custody"):
        service.boundary(tenant, b, p["executor_id"], "before_effect")


def test_configuration_and_readiness_rechecked_at_effect_boundary(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    b = service.prepare(tenant, job, "reserve")
    owners.authority_changes = {"configuration": p["configuration"] | {"revision": 2}}
    with pytest.raises(Rejected, match="authority"):
        service.boundary(tenant, b, p["executor_id"], "before_effect")
    owners.authority_changes = {}
    owners.omit = "commissioning"
    with pytest.raises(Rejected, match="incomplete"):
        service.boundary(tenant, b, p["executor_id"], "before_effect")
    assert not service.read(tenant, job)["operations"][0]["redeemed"]


def test_no_late_launch_or_step_skipping_and_heartbeat_can_exceed_minute(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    with pytest.raises(Rejected, match="stage_order"):
        service.prepare(tenant, job, "activate")
    b = service.prepare(tenant, job, "reserve")
    owners.now += 61
    with pytest.raises(Rejected, match="dispatch_expired"):
        service.boundary(tenant, b, p["executor_id"], "before_effect")


def test_separate_retirement_plan_and_retention_evidence_cannot_be_omitted(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    for stage in PROVISION:
        complete(service, p, tenant, job, stage)
    retire = deepcopy(p)
    retire.update(purpose="retire", source_job_id=job, intents={s: digest(s) for s in RETIRE})
    with pytest.raises(Rejected, match="separate_native_retirement"):
        service.admit(retire, str(uuid4()))
    retire.update(plan_digest="b" * 64, approval_id=str(uuid4()), plan_id=str(uuid4()))
    second = service.admit(retire, str(uuid4()))
    owners.omit = "retained_keys_readable"
    with pytest.raises(Rejected, match="incomplete"):
        service.prepare(tenant, second, "retire")
    with pytest.raises(Rejected, match="stage_order"):
        service.prepare(tenant, second, "release")


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM app.native_jobs",
        "DELETE FROM app.native_events",
        "DELETE FROM app.native_operations",
        "DELETE FROM app.native_redemptions",
        "UPDATE app.native_observations SET digest='changed'",
        "UPDATE app.native_control SET quarantined=false",
        "TRUNCATE app.native_resource_holds",
    ],
)
def test_runtime_cannot_rewrite_authority_or_certainty(
    native: Any, postgres: dict[str, Any], sql: str
) -> None:
    admitted(native)
    with psycopg.connect(**(postgres | {"user": "lifecycle_runtime"})) as c:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute(sql)


def native_http(
    service: NativeWorkflow, tenant: str, worker: str, body: dict[str, Any], token: str = "a" * 64
) -> tuple[int, dict[str, Any]]:
    import asyncio
    import json

    from uvicorn._types import ASGIReceiveEvent, ASGISendEvent, HTTPScope

    from lifecycle.interfaces.native import NativeBoundaryApp

    def caller(value: str) -> tuple[str, str]:
        if value != "a" * 64:
            raise Rejected("invalid_workload", 401)
        return tenant, worker

    scope: HTTPScope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/internal/native-grants/checks",
        "raw_path": b"/internal/native-grants/checks",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"authorization", ("Bearer " + token).encode()),
            (b"content-type", b"application/json"),
        ],
        "client": ("127.0.0.1", 8000),
        "server": ("127.0.0.1", 8080),
        "state": {},
    }
    events: list[ASGISendEvent] = []

    async def send(event: ASGISendEvent) -> None:
        events.append(event)

    async def receive() -> ASGIReceiveEvent:
        return {"type": "http.request", "body": json.dumps(body).encode(), "more_body": False}

    asyncio.run(NativeBoundaryApp(service, caller)(scope, receive, send))
    start, response = events
    assert start["type"] == "http.response.start" and response["type"] == "http.response.body"
    assert (b"cache-control", b"no-store, private") in start["headers"]
    return start["status"], json.loads(response["body"])


def test_native_http_identity_is_independent_of_body(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    complete(service, p, tenant, job, "reserve")
    binding = service.prepare(tenant, job, "provision")
    bound = binding["native_binding"]
    assert bound["project_id"] == p["scope"]["project_id"]
    assert bound["job_id"] == job and bound["operation_id"] == binding["operation_id"]
    body = {"grant": binding, "boundary": "before_saved_plan_apply"}
    status, reply = native_http(service, tenant, p["executor_id"], body, token="b" * 64)
    assert status == 401
    status, reply = native_http(service, tenant, str(uuid4()), body)
    assert status == 403
    status, reply = native_http(service, str(uuid4()), p["executor_id"], body)
    assert status == 404
    status, reply = native_http(
        service, tenant, p["executor_id"], body | {"worker_id": p["executor_id"]}
    )
    assert status == 409
    status, reply = native_http(service, tenant, p["executor_id"], body)
    assert status == 200 and reply["binding_sha256"] == digest(binding)
    status, reply = native_http(service, tenant, p["executor_id"], body)
    assert status == 423 and reply["error"] == "native_grant_already_redeemed"


def test_long_running_grant_remains_bound_and_rechecks_current_authority(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    b = service.prepare(tenant, job, "reserve")
    service.boundary(tenant, b, p["executor_id"], "before_effect")
    owners.now += 120
    assert service.boundary(tenant, b, p["executor_id"], "during_effect")["allowed"] is True
    owners.authority_changes = {"approval_current": False}
    with pytest.raises(Rejected, match="authority"):
        service.boundary(tenant, b, p["executor_id"], "during_effect")


def test_previous_stage_observation_cannot_clear_later_unknown_hold(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    prior = complete(service, p, tenant, job, "reserve")
    b = service.prepare(tenant, job, "provision")
    service.boundary(tenant, b, p["executor_id"], "before_saved_plan_apply")
    owners.failure = True
    with pytest.raises(Rejected):
        service.reconcile(tenant, b)
    assert service.reconcile(tenant, prior) == "held"
    assert service.read(tenant, job)["state"] == "held"
