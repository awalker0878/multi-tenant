"""Internal capability reads use their own UUID-scoped reauthorization."""

import asyncio
import json
from unittest.mock import Mock, patch
from uuid import uuid4

from inventory.interfaces.planning import PlanningInputApp


def test_capability_route_rechecks_capability_owner_not_native_revision_reader() -> None:
    tenant, application, environment, site, endpoint, generation = (
        str(uuid4()) for _ in range(6)
    )
    authority = Mock()
    capability = Mock()
    native = Mock()
    app = PlanningInputApp(
        Mock(), authority, native, Mock(), capability,
    )
    path = (
        f"/internal/tenants/{tenant}/planning-capability-inputs/"
        f"{application}/{environment}/{site}/{endpoint}/{generation}"
    )
    scope = {
        "type": "http", "method": "GET", "path": path,
        "query_string": b"",
        "headers": [(b"authorization", b"Bearer " + b"a" * 64)],
    }
    out = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict) -> None:
        out.append(event)

    with patch("inventory.interfaces.planning.capability_input",
               return_value={"tenant_id": tenant, "native_write_authorized": False}):
        asyncio.run(app(scope, receive, send))
    assert out[0]["status"] == 200
    assert json.loads(out[1]["body"])["native_write_authorized"] is False
    assert capability.call_count == 2
    native.assert_not_called()
    authority.assert_not_called()
