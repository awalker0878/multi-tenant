"""Execute real Inventory ASGI router with a database-backed Campaign fixture.

No Planning consumer evidence is earned by these owner-only assertions.
"""

from test_discovery import Campaign
from test_readiness_http import Authority, request

from inventory.infrastructure.migration_collection_evidence import read_collection_coverages
from inventory.interfaces.discovery import InventoryApp

pytest_plugins = ["test_discovery"]


def test_inventory_operator_readiness_owner_tenant_and_authority_boundaries(
    campaign: Campaign,
) -> None:
    authority = Authority(campaign.actor)
    app = InventoryApp(campaign.service, authority, None, read_collection_coverages)
    tenant = campaign.actor.tenant
    site = campaign.actor.site
    path = f"/v1/tenants/{tenant}/sites/{site}/operator-readiness"
    body = {
        "values": {"max_outage_seconds": 0},
        "configuration_digest": None,
        "context": {"operation": "migrate", "method": "VM_COLD_EXPORT"},
    }
    status, created = request(app, path, body)
    assert status == 201 and created["native_write_authorized"] is False
    status, viewed = request(app, path)
    assert status == 200 and viewed["context"] == body["context"]
    authority.denied = True
    assert request(app, path)[0] == 403
    assert request(app, path, body)[0] == 403
