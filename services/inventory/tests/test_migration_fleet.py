"""Real store tests for bulk selection, independent VM reviews and changed source custody."""

from dataclasses import replace
from typing import Any

import psycopg
import pytest
from test_discovery import Campaign
from test_workload_profiles import collected, review

from inventory.application.discovery import uid
from inventory.application.fleet import MigrationFleet
from inventory.application.workload import WorkloadProfiles
from inventory.domain.discovery import Rejected

pytest_plugins = ["test_discovery"]


def setup(c: Campaign) -> tuple[MigrationFleet, WorkloadProfiles, list[str], str]:
    sources = [collected(c, True), collected(c, True)]
    target = collected(c, False)
    return MigrationFleet(c.service), WorkloadProfiles(c.service), sources, target


def group_body(fleet: MigrationFleet, c: Campaign, target: str) -> dict[str, Any]:
    return {
        "name": "Application wave 1",
        "application_id": uid(),
        "environment_id": uid(),
        "target_profile_id": target,
        "format": "qcow2",
        "resource_ids": [
            v["resource_id"] for v in fleet.read(c.actor)["items"] if v["profile_id"] is not None
        ],
    }


def confirm(app: WorkloadProfiles, c: Campaign, source: str, target: str) -> dict[str, Any]:
    saved = app.command(c.actor, "migration_save", review(source, target), uid(), source)
    app.command(
        c.actor, "migration_confirm", {"digest": saved["digest"]}, uid(), source, saved["revision"]
    )
    return saved


def test_each_vm_keeps_its_confirmed_review_and_bulk_preparations_are_exact(
    campaign: Campaign,
) -> None:
    c = campaign
    fleet, app, sources, target = setup(c)
    receipts = [confirm(app, c, source, target) for source in sources]
    assert [r["revision"] for r in receipts] == [1, 2]
    for source, receipt in zip(sources, receipts, strict=True):
        assert app.read(c.actor, source)["review"]["revision"] == receipt["revision"]
        result = app.planning(
            c.actor.tenant, c.actor.site or "", receipt["revision"], receipt["digest"]
        )
        assert result["current"]
    body = group_body(fleet, c, target)
    saved = fleet.command(c.actor, "migration_group_save", body, uid())
    detail = MigrationFleet(c.service).detail(c.actor, saved["id"])
    assert not detail["native_write_authorized"]
    assert len(detail["members"]) == 2
    assert all(not m["holds"] and m["preparation"] for m in detail["members"])
    keys = [d["target_key"] for m in detail["members"] for d in m["preparation"]["disks"]]
    assert len(set(keys)) == len(keys)
    assert fleet.detail(c.actor, saved["id"]) == detail
    assert {m["preparation"]["review"]["revision"] for m in detail["members"]} == {1, 2}


def test_destination_inventory_remains_visible_without_a_source_profile(
    campaign: Campaign,
) -> None:
    c = campaign
    fleet, _, sources, target = setup(c)
    items = fleet.read(c.actor)["items"]
    assert len(items) == 3
    assert {item["profile_id"] for item in items if item["profile_id"]} == set(sources)
    unprofiled = next(item for item in items if item["profile_id"] is None)
    assert unprofiled["endpoint_id"] == c.endpoint
    assert "source_profile_required" in unprofiled["holds"]
    body = group_body(fleet, c, target) | {"resource_ids": [unprofiled["resource_id"]]}
    saved = fleet.command(c.actor, "migration_group_save", body, uid())
    member = fleet.detail(c.actor, saved["id"])["members"][0]
    assert member["preparation"] is None
    assert "source_profile_required" in member["holds"]


def test_group_replay_revision_and_cross_tenant_selection_are_enforced(campaign: Campaign) -> None:
    c = campaign
    fleet, _, _, target = setup(c)
    body, key = group_body(fleet, c, target), uid()
    saved = fleet.command(c.actor, "migration_group_save", body, key)
    assert fleet.command(c.actor, "migration_group_save", body, key) == saved
    with pytest.raises(Rejected, match="idempotency_conflict"):
        fleet.command(c.actor, "migration_group_save", body | {"name": "changed"}, key)
    with pytest.raises(Rejected, match="revision_required"):
        fleet.command(c.actor, "migration_group_save", body, uid(), saved["id"])
    with pytest.raises(Rejected, match="stale_revision"):
        fleet.command(c.actor, "migration_group_save", body, uid(), saved["id"], 2)
    updated = fleet.command(
        c.actor, "migration_group_save", body | {"name": "wave 2"}, uid(), saved["id"], 1
    )
    assert updated["revision"] == 2
    with pytest.raises(Rejected, match="not_found"):
        fleet.detail(replace(c.actor, tenant=uid()), saved["id"])
    assert fleet.read(replace(c.actor, tenant=uid()))["items"] == []
    with pytest.raises(Rejected, match="not_found"):
        fleet.command(c.actor, "migration_group_save", body | {"resource_ids": [uid()]}, uid())
    with pytest.raises(Rejected, match="action_denied"):
        fleet.read(replace(c.actor, action="inventory.read"))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with c.database.transaction() as tx:
            tx.execute("DELETE FROM inventory.migration_groups")


def test_one_held_member_does_not_hide_other_members_and_stale_target_holds_all(
    campaign: Campaign,
) -> None:
    c = campaign
    fleet, app, sources, target = setup(c)
    confirm(app, c, sources[0], target)
    saved = fleet.command(c.actor, "migration_group_save", group_body(fleet, c, target), uid())
    members = fleet.detail(c.actor, saved["id"])["members"]
    assert sum(m["preparation"] is not None for m in members) == 1
    assert sum("confirmed_vm_review_required" in m["holds"] for m in members) == 1
    c.now += 400
    assert all(m["preparation"] is None for m in fleet.detail(c.actor, saved["id"])["members"])
    c.now -= 400
    c.held = True
    assert all(m["preparation"] is None for m in fleet.detail(c.actor, saved["id"])["members"])


def test_group_binds_source_identity_and_rejects_manual_fact_injection(campaign: Campaign) -> None:
    c = campaign
    fleet, app, sources, target = setup(c)
    confirm(app, c, sources[0], target)
    body = group_body(fleet, c, target)
    for mutation in ({"native_write_authorized": True}, {"source_identity_sha256": "a" * 64}):
        with pytest.raises(Rejected, match="unknown_field"):
            fleet.command(c.actor, "migration_group_save", body | mutation, uid())
    with pytest.raises(Rejected, match="duplicate_migration_member"):
        fleet.command(
            c.actor,
            "migration_group_save",
            body | {"resource_ids": body["resource_ids"] * 2},
            uid(),
        )
    with pytest.raises(Rejected, match="migration_group_bound"):
        fleet.command(
            c.actor,
            "migration_group_save",
            body | {"resource_ids": [uid() for _ in range(51)]},
            uid(),
        )
    with pytest.raises(Rejected, match="source_review_scope_mismatch"):
        app.command(c.actor, "migration_save", review(sources[1], target), uid(), sources[0])
    saved = fleet.command(c.actor, "migration_group_save", body, uid())
    # A group created before complete profiles cannot silently adopt a newly observed identity.
    # Simulate the stored no-identity state through the owner-independent candidate seam.
    original = fleet.candidate
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            fleet, "candidate", lambda *args: original(*args) | {"source_identity_sha256": "f" * 64}
        )
        assert all(
            "group_source_identity_requires_review" in m["holds"]
            for m in fleet.detail(c.actor, saved["id"])["members"]
        )


def test_superseded_vm_review_is_denied_without_invalidating_another_vm(campaign: Campaign) -> None:
    c = campaign
    _, app, sources, target = setup(c)
    first, second = [confirm(app, c, source, target) for source in sources]
    app.command(
        c.actor, "migration_save", review(sources[0], target), uid(), sources[0], first["revision"]
    )
    with pytest.raises(Rejected, match="current_migration_review_required"):
        app.planning(c.actor.tenant, c.actor.site or "", first["revision"], first["digest"])
    assert app.planning(c.actor.tenant, c.actor.site or "", second["revision"], second["digest"])[
        "current"
    ]


def test_fleet_pages_discovered_machines_without_inventing_missing_profiles(
    campaign: Campaign,
) -> None:
    from test_workload_profiles import install, profile, read_request

    from inventory.application.profile_collection import authorize_read

    c = campaign
    install(c, True)
    c.start()
    for stream in range(3):
        c.now += 2
        lease = c.service.claim(c.worker)["job"]
        items = [c.item(native=f"vm-{i}") for i in range(1, 61)] if stream == 0 else []
        c.service.submit(c.worker, c.page(lease, items))
    c.now += 2
    lease = c.service.claim(c.worker)["job"]
    observed = c.now
    for request in range(1, 9):
        assert authorize_read(c.service, c.worker, read_request(lease, request))["allowed"]
        c.now += 1
    body = c.page(lease, []) | {"profile": profile(observed), "collected_at": observed}
    assert c.service.submit(c.worker, body)["status"] == "complete"
    fleet = MigrationFleet(c.service)
    first = fleet.read(c.actor)
    second = fleet.read(c.actor, first["next_cursor"])
    assert len(first["items"]) == 50 and len(second["items"]) == 10
    assert second["next_cursor"] is None
    items = first["items"] + second["items"]
    assert len({m["resource_id"] for m in items}) == 60
    assert sum("source_profile_required" in m["holds"] for m in items) == 59
