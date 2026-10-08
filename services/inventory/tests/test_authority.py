"""Authority decisions require an explicit JSON boolean, never a numeric equivalent."""

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import Mock

import pytest

from inventory.application.discovery import uid
from inventory.application.ports import Policies
from inventory.domain.discovery import Rejected
from inventory.infrastructure import authority


@pytest.mark.parametrize("caller", ["actor", "planning"])
@pytest.mark.parametrize("allowed", [True, 1, 1.0, False, None, "true", [], {}])
def test_authority_accepts_only_explicit_boolean_allow(
    monkeypatch: pytest.MonkeyPatch, caller: str, allowed: Any
) -> None:
    tenant, site, application, environment = (uid() for _ in range(4))
    action = "inventory.admin" if caller == "actor" else "plan.read"
    scope = {
        "site_id": site,
        "environment": None if caller == "actor" else environment,
        "resource_id": None if caller == "actor" else application,
    }
    body = {
        "allowed": allowed,
        "audience": "inventory" if caller == "actor" else "planning",
        "delegating_service": "console",
        "authority_use": "request_bound",
        "tenant_id": tenant,
        "action": action,
        "scope": scope,
        "source_owner": "inventory",
        "source_use": "planning_read_only",
        "actor_id": uid(),
        "delegation_id": uid(),
        "evaluated_at": datetime.fromtimestamp(1000, UTC).isoformat(),
        "expires_at": datetime.fromtimestamp(1060, UTC).isoformat(),
    }
    response = Mock()
    response.status = 200
    response.read.return_value = json.dumps(body).encode()
    response.getheader.return_value = "identity"
    connection = Mock()
    connection.getresponse.return_value = response
    monkeypatch.setenv("GOVERNANCE_URL", "https://governance.example")
    monkeypatch.setenv("GOVERNANCE_CA_FILE", "/synthetic/ca.pem")
    monkeypatch.setattr(
        "inventory.infrastructure.authority.http.client.HTTPSConnection",
        lambda *args, **kwargs: connection,
    )
    monkeypatch.setattr(
        "inventory.infrastructure.authority.ssl.create_default_context", lambda **kwargs: Mock()
    )
    monkeypatch.setattr("inventory.infrastructure.authority.time.time", lambda: 1000)
    monkeypatch.setattr(
        authority,
        "mounted_secret",
        lambda name: "outgoing" if name == "INVENTORY_GOVERNANCE_CREDENTIAL_FILE" else "incoming",
    )

    def check() -> None:
        if caller == "actor":
            result = authority.GovernanceAuthority(Mock(spec=Policies)).actor(
                "incoming", "a" * 64, tenant, action, site
            )
            assert result.actor == body["actor_id"]
        else:
            authority.planning_actor(
                "incoming", "a" * 64, tenant, action, application, environment, site
            )

    if allowed is True:
        check()
    else:
        with pytest.raises(Rejected, match="authority_unavailable"):
            check()
    connection.close.assert_called_once()
