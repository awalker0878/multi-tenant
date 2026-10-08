"""AHV enrollment, seven-read receipt, review and fleet over real PostgreSQL."""

import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from test_discovery import Campaign
from test_workload_profiles import collected, profile, read_request, review

from inventory.application.configuration import PortingConfiguration
from inventory.application.discovery import uid
from inventory.application.fleet import MigrationFleet
from inventory.application.profile_collection import authorize_read
from inventory.application.workload import WorkloadProfiles
from inventory.domain.configuration import AHV_CAPABILITIES
from inventory.domain.discovery import Rejected
from inventory.infrastructure.policies import parse_policy

pytest_plugins = ["test_discovery"]


@pytest.mark.parametrize("operation", ["discover", "configuration_pull"])
def test_ahv_destination_roundtrip_binds_profiles_and_revokes_with_enrollment(
    campaign: Campaign, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    c = campaign
    monkeypatch.setattr(
        "test_workload_profiles.profile",
        lambda now, source=True: profile(now, source) | {"firmware": "bios"},
    )
    source = collected(c, True)
    fixture = json.loads(
        (
            Path(__file__).parents[3] / "contracts/fixtures/inventory/ahv-destination-v1.json"
        ).read_text()
    )
    target = fixture["target"]
    document = asdict(c.policy)
    document.pop("policy_digest")
    base = document["streams"][0]
    document.update(
        policy_id=uid(),
        platform="ahv",
        native_scope=target["project_id"],
        streams=[
            {
                **base,
                "kind": "target_profile",
                "base_url": "https://native.example",
                "api_version": "v4.3",
                "cluster_id": target["cluster_id"],
                "prism_central_id": target["prism_central_id"],
                "shared_resource_ids": [],
            }
        ],
    )
    c.policy = parse_policy(document)
    c.policies.values[c.policy.policy_id] = c.policy
    c.endpoint = c.service.command(
        c.actor, "enroll", {"policy_id": c.policy.policy_id, "label": "AHV lab"}, uid()
    )["endpoint_id"]
    c.service.command(
        replace(
            c.actor,
            action="inventory.discover" if operation == "discover" else "inventory.admin",
        ),
        operation,
        {},
        uid(),
        c.endpoint,
    )
    c.now += 2
    lease = c.service.claim(c.worker)["job"]
    observed = c.now
    for request in range(1, 8):
        assert authorize_read(c.service, c.worker, read_request(lease, request))["allowed"]
        c.now += 1
    target["observed_at"] = int(observed)
    body = c.page(lease, []) | {"profile": target, "collected_at": observed}
    assert c.service.submit(c.worker, body)["status"] == "complete"
    app, fleet = WorkloadProfiles(c.service), MigrationFleet(c.service)
    profile_id = next(
        p["id"] for p in app.read(c.actor)["profiles"] if p["endpoint_id"] == c.endpoint
    )
    form = review(source, profile_id)
    # Existing source fixture has one boot disk and no NICs.
    form["destination"] = fixture["review"]["destination"] | {
        "disks": [{"source_key": 2000, "index": 0}],
        "nics": [],
    }
    saved = app.command(c.actor, "migration_save", form, uid(), source)
    app.command(
        c.actor, "migration_confirm", {"digest": saved["digest"]}, uid(), source, saved["revision"]
    )
    planning = app.planning(c.actor.tenant, c.actor.site or "", saved["revision"], saved["digest"])
    assert planning["destination"] == form["destination"]
    assert fleet.read(c.actor)["targets"][0]["platform"] == "ahv"
    cfg = PortingConfiguration(c.service)
    cfg.command(
        c.actor,
        "configuration_save",
        {
            "source_endpoint": None,
            "target_endpoint": c.endpoint,
            "manual": {},
            "choices": [
                {"id": cap["id"], "required": True, "interpretation": "observed", "reason": ""}
                for cap in AHV_CAPABILITIES
            ],
        },
        uid(),
    )
    workspace = cfg.read(c.actor)
    assert workspace["target"]["current"]
    assert workspace["ahv_capabilities"][0]["target_state"] == "configured"
    with pytest.raises(Rejected):
        app.read(replace(c.actor, tenant=uid()), source)
    c.service.command(c.actor, "revoke", {}, uid(), c.endpoint, 1)
    with pytest.raises(Rejected, match="current_migration_review_required"):
        app.planning(c.actor.tenant, c.actor.site or "", saved["revision"], saved["digest"])
