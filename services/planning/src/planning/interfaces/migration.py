"""Authenticated migration preparation; returns bindings, never execution authority."""

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from planning.application.migration_plans import MigrationPlans
from planning.application.migration_flows import MigrationFlows
from planning.application.migration_support import MigrationSupport
from planning.application.ports import Authority
from planning.domain.model import Rejected, decode, identifier, integer, sha, shape
from planning.interfaces.planning import UUID, single


class MigrationPreparationApp:
    def __init__(
        self,
        authority: Authority,
        prepare: Callable[..., dict[str, Any]],
        plans: MigrationPlans | None = None,
        support: MigrationSupport | None = None,
        flows: MigrationFlows | None = None,
    ) -> None:
        self.authority, self.prepare = authority, prepare
        self.plans, self.support, self.flows = plans, support, flows

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        try:
            route = re.fullmatch(
                rf"/v1/tenants/({UUID})/applications/({UUID})/environments/({UUID})/(migration-preparations|migration-plans|migration-plan-options|migration-support|migration-flow-choices|migration-flow-selections)",
                scope["path"],
            )
            if route is None or scope["method"] != "POST" or scope["query_string"]:
                raise Rejected("not_found", 404)
            headers = list(scope["headers"])
            auth = single(headers, b"authorization")
            if len(headers) > 40 or not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", auth):
                raise Rejected("invalid_workload", 401)
            if single(headers, b"content-type").split(";")[0] != "application/json" or single(
                headers, b"content-encoding", True
            ):
                raise Rejected("unsupported_content_type", 415)
            await asyncio.to_thread(self.authority.caller, auth[7:])
            chunks = bytearray()
            async with asyncio.timeout(5):
                while True:
                    event = await receive()
                    if event["type"] != "http.request":
                        raise Rejected("interrupted", 400)
                    chunks.extend(event["body"])
                    if len(chunks) > 32768:
                        raise Rejected("request_bound", 413)
                    if not event.get("more_body", False):
                        break
            complete = route[4] == "migration-plans"
            flow_read = route[4] == "migration-flow-choices"
            flow_save = route[4] == "migration-flow-selections"
            body = shape(
                decode(bytes(chunks)),
                ({"site_id"} if route[4] in {"migration-support", "migration-flow-choices"}
                 else {"site_id", "revision", "context_sha256", "selections", "omissions"} if flow_save
                 else {"site_id", "review", "disks"})
                | ({"base_plan_id", "recipe_id"} if complete else set()),
            )
            review = shape(body["review"], {"revision", "digest"}) if "review" in body else {}
            site = identifier(body["site_id"])
            tenant, application, environment = route.groups()[:3]
            delegation = single(headers, b"x-actor-delegation")
            actor = await asyncio.to_thread(
                self.authority.actor,
                auth[7:],
                delegation,
                tenant,
                "plan.read" if route[4] in {"migration-support", "migration-flow-choices"} else "plan.create",
                application,
                environment,
                site,
            )
            if route[4] == "migration-support":
                if self.support is None:
                    raise Rejected("migration_support_unavailable", 503)
                payload = await asyncio.to_thread(self.support.read, actor, site)
                status = 200
            elif flow_read or flow_save:
                if self.flows is None:
                    raise Rejected("migration_flow_service_unavailable", 503)
                if flow_read:
                    payload = await asyncio.to_thread(self.flows.read, actor, site, delegation)
                    status = 200
                else:
                    payload = await asyncio.to_thread(
                        self.flows.save, actor, site, delegation, body,
                        identifier(single(headers, b"idempotency-key")),
                    )
                    status = 200
            elif route[4] == "migration-plan-options":
                if self.plans is None:
                    raise Rejected("migration_plan_composition_unavailable", 503)
                payload = await asyncio.to_thread(self.plans.options, actor, body, delegation)
                status = 200
            elif complete:
                if self.plans is None:
                    raise Rejected("migration_plan_composition_unavailable", 503)
                payload = await asyncio.to_thread(
                    self.plans.create,
                    actor,
                    body,
                    identifier(single(headers, b"idempotency-key")),
                    delegation,
                )
                status = 201
            else:
                binding = await asyncio.to_thread(
                    self.prepare,
                    tenant,
                    application,
                    environment,
                    site,
                    integer(review["revision"], 1),
                    sha(review["digest"]),
                    delegation,
                    body["disks"],
                )
                payload = {"binding": binding, "native_write_authorized": False}
                status = 200
        except Rejected as e:
            status, payload = e.status, {"error": e.reason}
        except Exception:
            status, payload = 503, {"error": "migration_preparation_unavailable"}
        raw = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store, private"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": raw})
