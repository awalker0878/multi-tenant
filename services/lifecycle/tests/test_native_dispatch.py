"""Native admission/dispatch persistence and activity rejection boundaries."""

import asyncio
from copy import deepcopy
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.exceptions import ApplicationError, WorkflowAlreadyStartedError
from test_native_workflow import admitted, complete
from test_native_workflow import native as native

from lifecycle.domain.execution import Rejected
from lifecycle.infrastructure.native_temporal import NativeActivities, NativeDispatcher


class Effects:
    def __init__(self) -> None:
        self.grants: list[dict[str, Any]] = []

    def execute(self, grant: dict[str, Any]) -> None:
        self.grants.append(deepcopy(grant))


class Description:
    workflow_type = "NativeJourneyV1"
    task_queue = "p07-native-v1"
    run_id = str(uuid4())

    def __init__(self, memo: dict[str, Any]) -> None:
        self.memo = memo

    async def memo_value(self, key: str, default: Any) -> Any:
        return self.memo.get(key, default)


class Handle:
    def __init__(self, description: Description) -> None:
        self.description = description

    async def describe(self, **kwargs: Any) -> Description:
        return self.description


class Client:
    def __init__(self) -> None:
        self.starts: list[dict[str, Any]] = []
        self.handles: dict[str, Handle] = {}
        self.lose_response = False
        self.changes: dict[str, Any] = {}

    async def start_workflow(self, method: Any, binding: Any, **kwargs: Any) -> Handle:
        self.starts.append(kwargs)
        key = kwargs["id"]
        if key in self.handles:
            raise WorkflowAlreadyStartedError(key, "NativeJourneyV1")
        description = Description(kwargs["memo"] | self.changes)
        self.handles[key] = Handle(description)
        if self.lose_response:
            self.lose_response = False
            raise TimeoutError("synthetic_accepted_start_response_lost")
        return self.handles[key]

    def get_workflow_handle(self, key: str) -> Handle:
        return self.handles[key]


def test_admission_dispatch_is_atomic_and_same_key_does_not_requeue(native: Any) -> None:
    service, owners, p = native
    command = str(uuid4())
    first = service.admit(p, command)
    assert service.admit(p, command) == first
    with service.database.transaction() as tx:
        rows = tx.all("SELECT * FROM app.native_dispatch", ())
    assert len(rows) == 1 and rows[0]["workflow_id"] == "p07-native-v1-" + first
    assert not rows[0]["dispatched"] and rows[0]["attempts"] == 0
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with service.database.transaction() as tx:
            tx.execute("UPDATE app.native_dispatch SET workflow_id='other'", ())
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with service.database.transaction() as tx:
            tx.execute("DELETE FROM app.native_dispatch", ())


def test_lost_dispatch_reply_keeps_same_identity_and_confirms_remote_memo(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    client: Any = Client()
    client.lose_response = True
    dispatcher = NativeDispatcher(service.database, client)
    with pytest.raises(TimeoutError):
        asyncio.run(dispatcher.dispatch())
    with service.database.transaction() as tx:
        row = tx.one("SELECT * FROM app.native_dispatch WHERE job=%s", (job,))
    assert row and not row["dispatched"] and row["attempts"] == 1
    assert asyncio.run(dispatcher.dispatch()) == 1
    assert asyncio.run(dispatcher.dispatch()) == 0
    assert len(client.handles) == 1
    for start in client.starts:
        assert start["id"] == "p07-native-v1-" + job
        assert start["id_reuse_policy"] == WorkflowIDReusePolicy.REJECT_DUPLICATE
        assert start["id_conflict_policy"] == WorkflowIDConflictPolicy.FAIL


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_id", str(uuid4())),
        ("tenant_id", str(uuid4())),
        ("plan_sha256", "f" * 64),
        ("version", True),
    ],
)
def test_dispatch_does_not_adopt_foreign_workflow(native: Any, field: str, value: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    client: Any = Client()
    client.changes[field] = value
    with pytest.raises(ValueError, match="native_workflow_identity_conflict"):
        asyncio.run(NativeDispatcher(service.database, client).dispatch())
    with service.database.transaction() as tx:
        row = tx.one("SELECT dispatched FROM app.native_dispatch WHERE job=%s", (job,))
    assert row and not row["dispatched"]


def test_stopped_admission_never_enters_temporal(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    service.stop(tenant, job)
    client: Any = Client()
    assert asyncio.run(NativeDispatcher(service.database, client).dispatch()) == 0
    assert not client.starts


def test_checkpoint_never_reissues_prepared_or_held_grant(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    assert service.checkpoint(tenant, job)["stage"] == "reserve"
    grant = service.prepare(tenant, job, "reserve")
    assert service.checkpoint(tenant, job)["grant"] == grant
    assert service.checkpoint(tenant, job)["action"] == "reconcile"
    service.hold(tenant, job)
    assert service.checkpoint(tenant, job)["action"] == "wait"
    with pytest.raises(Rejected):
        service.prepare(tenant, job, "reserve")
    with pytest.raises(Rejected):
        service.checkpoint(str(uuid4()), job)


def test_worker_return_cannot_establish_readiness_or_redeem_grant(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    effects = Effects()
    activities = NativeActivities(service, effects)
    args = {"tenant": tenant, "job": job}
    grant = activities.prepare(args | {"stage": "reserve"})
    assert activities.effect(args | {"grant": grant}) == {"submitted": True}
    assert len(effects.grants) == 1
    with pytest.raises(ApplicationError, match="native_operation_held"):
        activities.reconcile(args | {"grant": grant})
    assert service.read(tenant, job)["state"] == "held"
    assert not service.read(tenant, job)["operations"][0]["redeemed"]


def test_activity_rejects_cross_job_and_revoked_authority_before_transport(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    effects = Effects()
    activities = NativeActivities(service, effects)
    grant = service.prepare(tenant, job, "reserve")
    for args in (
        {"tenant": str(uuid4()), "job": job, "grant": grant},
        {"tenant": tenant, "job": str(uuid4()), "grant": grant},
        {"tenant": tenant, "job": job, "grant": grant | {"executor_id": str(uuid4())}},
    ):
        with pytest.raises(ApplicationError):
            activities.effect(args)
    owners.authority_changes["approval_current"] = False
    with pytest.raises(ApplicationError) as held:
        activities.effect({"tenant": tenant, "job": job, "grant": grant})
    assert held.value.non_retryable and not effects.grants


def test_checkpoint_next_stage_requires_independent_completion(native: Any) -> None:
    service, owners, p, tenant, job = admitted(native)
    complete(service, p, tenant, job, "reserve")
    assert service.checkpoint(tenant, job)["stage"] == "provision"
    service.stop(tenant, job)
    assert service.checkpoint(tenant, job)["state"] == "stopped"


def test_activity_failure_does_not_expose_owner_exception() -> None:
    class Broken:
        def checkpoint(self, tenant: str, job: str) -> dict[str, Any]:
            raise OSError("private_credential_and_provider_response")

    control: Any = Broken()
    activities = NativeActivities(control, Effects())
    with pytest.raises(ApplicationError) as error:
        activities.checkpoint({"tenant": str(uuid4()), "job": str(uuid4())})
    assert str(error.value) == "native_operation_held"
    assert error.value.non_retryable
