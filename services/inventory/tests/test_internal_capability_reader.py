"""Internal capability reads use their own UUID-scoped reauthorization."""

import asyncio
import json
from typing import Any, cast
from unittest.mock import Mock, patch
from uuid import uuid4

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from inventory.interfaces.planning import PlanningInputApp


def test_capability_route_rechecks_capability_owner_not_native_revision_reader() -> None:
    tenant, application, environment, site, endpoint, generation = (str(uuid4()) for _ in range(6))
    authority = Mock()
    capability = Mock()
    native = Mock()
    app = PlanningInputApp(
        Mock(),
        authority,
        native,
        Mock(),
        capability,
    )
    path = (
        f"/internal/tenants/{tenant}/planning-capability-inputs/"
        f"{application}/{environment}/{site}/{endpoint}/{generation}"
    )
    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": [(b"authorization", b"Bearer " + b"a" * 64)],
    }
    out: list[Any] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, Any]) -> None:
        out.append(event)

    with patch(
        "inventory.interfaces.planning.capability_input",
        return_value={"tenant_id": tenant, "native_write_authorized": False},
    ):
        asyncio.run(
            app(
                cast(Scope, scope), cast(ASGIReceiveCallable, receive), cast(ASGISendCallable, send)
            )
        )
    assert out[0]["status"] == 200
    assert json.loads(out[1]["body"])["native_write_authorized"] is False
    assert capability.call_count == 2
    native.assert_not_called()
    authority.assert_not_called()
