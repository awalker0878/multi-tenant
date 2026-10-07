"""Authenticated campaign control; metrics and capacity are never accepted from the Console."""

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qsl

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle.application.campaigns import Campaigns
from lifecycle.application.execution_ports import RequestAuthority
from lifecycle.domain.execution import Rejected, decode, identity
from lifecycle.domain.native_workflow import checksum, exact, integer
from lifecycle.interfaces.execution import UUID, single


class CampaignApp:
    def __init__(
        self,
        campaigns: Campaigns,
        authority: RequestAuthority,
        member_source: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.campaigns, self.authority, self.member_source = campaigns, authority, member_source

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        payload: dict[str, Any]
        try:
            route = re.fullmatch(
                rf"/v1/tenants/({UUID})/migration-campaigns(?:/({UUID}))?(?:/(commands))?",
                scope["path"],
            )
            if route is None or scope["method"] not in {"GET", "POST"}:
                raise Rejected("not_found", 404)
            headers = list(scope["headers"])
            if len(headers) > 40 or any(k.lower() == b"content-encoding" for k, _ in headers):
                raise Rejected("request_bound", 413)
            auth = single(headers, b"authorization")
            if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", auth):
                raise Rejected("invalid_workload", 401)
            await asyncio.to_thread(self.authority.caller, auth[7:], "console")
            tenant, campaign, command = route.groups()
            query = parse_qsl(scope["query_string"].decode("ascii"), strict_parsing=True)
            if query and (campaign or scope["method"] != "GET"):
                raise Rejected("not_found", 404)
            body: dict[str, Any] = {}
            if scope["method"] == "POST":
                if single(headers, b"content-type").split(";")[0] != "application/json":
                    raise Rejected("unsupported_content_type", 415)
                raw = bytearray()
                async with asyncio.timeout(5):
                    while True:
                        event = await receive()
                        if event["type"] != "http.request":
                            raise Rejected("interrupted", 400)
                        raw.extend(event["body"])
                        if len(raw) > 262144:
                            raise Rejected("campaign_request_bound", 413)
                        if not event.get("more_body", False):
                            break
                body = decode(bytes(raw))
            if campaign:
                current = await asyncio.to_thread(self.campaigns.read, tenant, campaign)
                requested_scope = current["scope"]
                action = "operation.read" if scope["method"] == "GET" else "operation.control"
            else:
                if command:
                    raise Rejected("not_found", 404)
                if scope["method"] == "POST":
                    exact(body, {"scope", "settings", "members"})
                    requested_scope = body["scope"]
                else:
                    if len(query) != 3:
                        raise Rejected("campaign_scope_required", 422)
                    requested_scope = dict(query)
                exact(requested_scope, {"site_id", "environment", "resource_id"})
                for value in requested_scope.values():
                    identity(value)
                action = "operation.admit" if scope["method"] == "POST" else "operation.read"
            actor = await asyncio.to_thread(
                self.authority.actor,
                single(headers, b"x-actor-delegation"),
                tenant,
                action,
                requested_scope,
            )
            if scope["method"] == "GET" and campaign and not command:
                payload, status = current, 200
            elif scope["method"] == "GET" and not campaign:
                rows = await asyncio.to_thread(self.campaigns.list, tenant, requested_scope)
                payload, status = (
                    {
                        "items": rows[:100],
                        "limit_reached": len(rows) > 100,
                        "tenant_id": tenant,
                        "scope": requested_scope,
                    },
                    200,
                )
            elif campaign and command and scope["method"] == "POST":
                exact(body, {"action", "expected_revision"})
                payload = await asyncio.to_thread(
                    self.campaigns.command,
                    tenant,
                    campaign,
                    actor,
                    identity(single(headers, b"idempotency-key")),
                    body["action"],
                    integer(body["expected_revision"], 1),
                )
                status = 202
            elif not campaign:
                refs = body["members"]
                if not isinstance(refs, list) or not 1 <= len(refs) <= 1000:
                    raise Rejected("campaign_member_bound", 422)
                members = []
                for ref in refs:
                    exact(
                        ref,
                        {
                            "id",
                            "plan_id",
                            "plan_revision",
                            "plan_digest",
                            "approval_id",
                            "depends_on",
                            "outage_group",
                            "priority",
                            "not_before",
                            "deadline",
                        },
                    )
                    for key in ("id", "plan_id", "approval_id"):
                        identity(ref[key])
                    checksum(ref["plan_digest"])
                    integer(ref["plan_revision"], 1)
                    observed = await asyncio.to_thread(self.member_source, tenant, ref)
                    if observed["scope"] != requested_scope or observed["requested_by"] != actor:
                        raise Rejected("campaign_plan_scope_changed", 403)
                    # Sizes, pools, route, mode and method originate from the authenticated plan.
                    members.append(ref | observed["requirements"])
                payload = await asyncio.to_thread(
                    self.campaigns.create,
                    tenant,
                    actor,
                    requested_scope,
                    body["settings"],
                    members,
                    identity(single(headers, b"idempotency-key")),
                )
                status = 202
            else:
                raise Rejected("not_found", 404)
        except Rejected as error:
            payload, status = {"error": error.reason}, error.status
        except (ValueError, TypeError, KeyError, UnicodeError, TimeoutError):
            payload, status = {"error": "invalid_campaign_request"}, 422
        except Exception:
            payload, status = {"error": "campaign_unavailable"}, 503
        response = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store, private"),
                    (b"content-length", str(len(response)).encode()),
                    (b"x-content-type-options", b"nosniff"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": response})
