"""Native admissions require both the exact approved executor and current scoped caller."""

import asyncio
import json
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from test_native_workflow import plan

from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.domain.execution import Rejected
from lifecycle.interfaces.native_jobs import NativeJobsApp


def request(
    app: NativeJobsApp, path: str, body: Any = None, *, method: str = "POST"
) -> tuple[int, Any]:
    sent: list[Any] = []

    async def run() -> None:
        scope: Any = {
            "type": "http",
            "path": path,
            "method": method,
            "query_string": b"",
            "headers": [
                (b"authorization", b"Bearer " + b"a" * 64),
                (b"x-actor-delegation", b"b" * 64),
                (b"content-type", b"application/json"),
                (b"idempotency-key", str(uuid4()).encode()),
            ],
        }

        async def receive() -> Any:
            return {"type": "http.request", "body": json.dumps(body).encode(), "more_body": False}

        async def send(value: Any) -> None:
            sent.append(value)

        await app(scope, receive, send)

    asyncio.run(run())
    return sent[0]["status"], json.loads(sent[1]["body"])


def setup() -> tuple[NativeJobsApp, Any, Any, Any, str, dict[str, Any]]:
    p = plan()
    workflow, authority, resolver = Mock(spec=NativeWorkflow), Mock(), Mock(return_value=p)
    authority.actor.return_value = p["actor_id"]
    workflow.admit.return_value = str(uuid4())
    workflow.read.return_value = {
        "job_id": workflow.admit.return_value,
        "scope": p["scope"],
        "revision": 1,
    }
    app = NativeJobsApp(workflow, authority, resolver)
    path = "/v1/tenants/" + p["scope"]["tenant_id"] + "/native-jobs"
    body = {k: p[k] for k in ("plan_id", "plan_revision", "plan_digest", "approval_id")}
    return app, workflow, authority, resolver, path, body


def test_complete_native_job_admission_reads_and_binds_approved_owner_plan() -> None:
    app, workflow, authority, resolver, path, body = setup()
    assert request(app, path, body)[0] == 202
    assert workflow.admit.call_args.args[0] == resolver.return_value
    assert authority.actor.call_args.args[2] == "operation.admit"


@pytest.mark.parametrize("fault", ["actor", "workload", "scope", "migration", "inline_plan"])
def test_native_http_denies_wrong_executor_and_campaign_bypass_before_admission(fault: str) -> None:
    app, workflow, authority, resolver, path, body = setup()
    if fault == "actor":
        authority.actor.return_value = str(uuid4())
    elif fault == "workload":
        authority.caller.side_effect = Rejected("denied", 401)
    elif fault == "scope":
        authority.actor.side_effect = Rejected("denied", 403)
    elif fault == "migration":
        resolver.return_value["purpose"] = "migrate"
    else:
        body["intents"] = {"injected": "value"}
    assert request(app, path, body)[0] in {401, 403, 422, 423}
    workflow.admit.assert_not_called()


def test_stop_requires_current_control_authority_and_expected_revision() -> None:
    app, workflow, authority, _, path, _ = setup()
    job = workflow.admit.return_value
    assert request(app, path + "/" + job + "/stop", {"expected_revision": 1})[0] == 202
    assert workflow.stop.call_args.args[-1] == 1
    assert authority.actor.call_args.args[2] == "operation.control"
    authority.actor.side_effect = Rejected("denied", 403)
    workflow.stop.reset_mock()
    assert request(app, path + "/" + job + "/stop", {"expected_revision": 1})[0] == 403
    workflow.stop.assert_not_called()
