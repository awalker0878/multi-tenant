"""An accepted workload with an unusable actor grant remains forbidden."""

from unittest.mock import Mock

import pytest

from lifecycle.domain.execution import Rejected
from lifecycle.infrastructure import execution_owners


@pytest.mark.parametrize("upstream,expected", [(401, 403), (403, 403), (404, 404), (503, 503)])
def test_current_delegation_denial_is_not_reclassified_as_workload_authentication(
    monkeypatch: pytest.MonkeyPatch, upstream: int, expected: int
) -> None:
    request = Mock(side_effect=Rejected("owner_denied", upstream))
    monkeypatch.setattr(execution_owners, "request", request)
    scope = {"site_id": "site", "environment": "environment", "resource_id": "application"}
    with pytest.raises(Rejected) as rejected:
        execution_owners.ExecutionOwners().actor("a" * 64, "tenant", "operation.read", scope)
    assert rejected.value.status == expected
    request.assert_called_once_with(
        "GOVERNANCE",
        "POST",
        "/v1/tenants/tenant/delegated-authorizations",
        {"action": "operation.read", "scope": scope},
        "a" * 64,
    )
