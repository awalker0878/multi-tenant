"""Profile custody, current authority, all-dataset review and immutable admission inputs."""

from dataclasses import asdict, replace
from typing import Any

import psycopg
import pytest
from test_discovery import Campaign, row

from inventory.application.discovery import uid
from inventory.application.profile_collection import authorize_read
from inventory.application.workload import WorkloadProfiles
from inventory.domain.discovery import Rejected
from inventory.domain.workload import OWNER_FIELDS, SOURCE_FIELDS, TARGET_FIELDS, review_input
from inventory.infrastructure.policies import parse_policy

pytest_plugins = ["test_discovery"]


def profile(now: float, source: bool = True) -> dict[str, Any]:
    p: dict[str, Any] = dict.fromkeys(SOURCE_FIELDS if source else TARGET_FIELDS)
    p.update(
        schema_version=1,
        profile_type="SourceWorkloadProfile" if source else "TargetCapabilityProfile",
        platform="vmware" if source else "openstack",
        observed_at=int(now),
        observations_sha256="a" * 64,
        holds=[],
        native_qualification="not_established",
    )
    if source:
        p.update(
            vm_id="vm-1",
            instance_uuid=uid(),
            bios_uuid=uid(),
            vcenter_uuid=uid(),
            vcenter_version="9.1.1",
            api_version="9.1.1.0",
            native_api_version="9.1.1.0",
            config_sha256="b" * 64,
            power_state="poweredOff",
            guest_id="otherLinux64Guest",
            firmware="efi",
            cpu=2,
            memory_mb=4096,
            nics=[],
            controllers=[],
            disks=[
                {
                    "key": 2000,
                    "capacity_bytes": 1048576,
                    "controller_key": 1000,
                    "unit_number": 0,
                    "backing_chain": [],
                    "native_sha256": "c" * 64,
                }
            ],
            snapshot_tree_sha256="d" * 64,
            key_custody_sha256="e" * 64,
            required_owner_inputs=[],
        )
    else:
        p.update(
            project_id="project-a",
            disk_formats=["raw", "qcow2"],
            image_import_methods=["glance-direct"],
            flavors=[],
            volume_types=[],
            network_extensions=[],
            compute_version={"version": "2.100", "min_version": "2.1"},
            volume_version={"version": "3.75", "min_version": "3.0"},
            required_capability_evidence=["guest_driver_profile"],
            security_groups=[],
        )
    return p


def install(c: Campaign, source: bool) -> None:
    document = asdict(c.policy)
    document.pop("policy_digest")
    document.update(
        policy_id=uid(),
        platform="vmware" if source else "openstack",
        native_scope="datacenter-1" if source else "project-a",
    )
    base = document["streams"][0]
    document["streams"] = [
        {
            **base,
            "kind": kind,
            "base_url": "https://native.example"
            + (
                ""
                if source
                else "/v3/project-a"
                if kind == "volume"
                else "/v2.0"
                if kind == "network"
                else "/v2.1"
            ),
            "api_version": "vcenter-api"
            if source
            else "3.0"
            if kind == "volume"
            else "2.0"
            if kind == "network"
            else "2.1",
        }
        for kind in ("server", "network", "datastore" if source else "volume")
    ]
    document["streams"].append(
        {
            **base,
            "kind": "source_profile" if source else "target_profile",
            "base_url": "https://native.example" + ("" if source else "/v2"),
            "api_version": "9.1.1.0" if source else "2",
            **({"vm_ids": ["vm-1"]} if source else {}),
        }
    )
    c.policy = parse_policy(document)
    c.policies.values[c.policy.policy_id] = c.policy
    c.endpoint = c.service.command(
        c.actor, "enroll", {"policy_id": c.policy.policy_id, "label": "Profile site"}, uid()
    )["endpoint_id"]


def pending(c: Campaign, listed: bool = True) -> dict[str, Any]:
    c.start()
    for i in range(3):
        c.now += 2
        lease = c.service.claim(c.worker)["job"]
        c.service.submit(
            c.worker, c.page(lease, [c.item(native="vm-1")] if i == 0 and listed else [])
        )
    c.now += 2
    return dict(c.service.claim(c.worker)["job"])


def read_request(lease: dict[str, Any], request: int) -> dict[str, Any]:
    return {k: lease[k] for k in ("discovery_id", "lease_token", "sequence")} | {
        "request_number": request
    }


def collected(c: Campaign, source: bool) -> str:
    install(c, source)
    lease = pending(c)
    observed = c.now
    for request in range(1, 9 if source else 8):
        assert authorize_read(c.service, c.worker, read_request(lease, request))["allowed"]
        c.now += 1
    body = c.page(lease, [])
    body.update(profile=profile(observed, source), collected_at=observed)
    assert c.service.submit(c.worker, body)["status"] == "complete"
    app = WorkloadProfiles(c.service)
    return str(
        next(p["id"] for p in app.read(c.actor)["profiles"] if p["endpoint_id"] == c.endpoint)
    )


def review(source: str, target: str) -> dict[str, Any]:
    return {
        "source_profile_id": source,
        "target_profile_id": target,
        "method": "VM_COLD_EXPORT",
        "datasets": [
            {
                "id": uid(),
                "name": "Complete boot and application disk",
                "disk_keys": [2000],
                "mounts": ["/"],
                "consistency_group": "application-1",
                "validation_reference": "owner-check-1",
            }
        ],
        "owner_inputs": dict.fromkeys(OWNER_FIELDS, "owner-protocol-reference"),
        "objectives": {
            "owner_id": uid(),
            "acceptance_sha256": "f" * 64,
            "max_outage_seconds": 3600,
            "max_data_loss_bytes": 0,
        },
        "overrides": [],
    }


def test_native_facts_and_incomplete_disks_cannot_be_manually_accepted() -> None:
    source = profile(1000)
    for fault in ("native_field", "missing_disk", "duplicate_dataset", "native_override"):
        body = review(uid(), uid())
        if fault == "native_field":
            body["cpu"] = 8
        elif fault == "missing_disk":
            body["datasets"][0]["disk_keys"] = [2001]
        elif fault == "duplicate_dataset":
            body["datasets"] *= 2
        else:
            body["overrides"] = [{"field": "firmware", "interpretation": "efi", "reason": "guess"}]
        with pytest.raises(Rejected):
            review_input(body, source)


def test_mandatory_console_owner_fields_enforced_by_inventory_not_only_vue() -> None:
    source = profile(1000)
    for field in OWNER_FIELDS:
        document = review(uid(), uid())
        document["owner_inputs"][field] = ""
        if field == "delta_protocol":
            # Cold-export does not require an invented delta protocol.
            review_input(document, source)
            document["method"] = "VM_SNAPSHOT_BASELINE_APP_DELTA"
        with pytest.raises(Rejected):
            review_input(document, source)
    for mutation in ("dataset_mapping", "owner_approval", "outage", "data_loss"):
        document = review(uid(), uid())
        if mutation == "dataset_mapping":
            document["datasets"][0]["disk_keys"] = []
        elif mutation == "owner_approval":
            document["objectives"]["acceptance_sha256"] = ""
        elif mutation == "outage":
            document["objectives"]["max_outage_seconds"] = -1
        else:
            document["objectives"]["max_data_loss_bytes"] = -1
        with pytest.raises(Rejected):
            review_input(document, source)


def test_profile_collection_charges_each_read_and_denies_replay_and_revocation(
    campaign: Campaign,
) -> None:
    c = campaign
    install(c, True)
    lease = pending(c)
    assert authorize_read(c.service, c.worker, read_request(lease, 1))["allowed"]
    assert not authorize_read(c.service, c.worker, read_request(lease, 2))["allowed"]
    c.now += 1
    assert authorize_read(c.service, c.worker, read_request(lease, 2))["allowed"]
    with pytest.raises(Rejected, match="profile_request_not_admitted"):
        authorize_read(c.service, c.worker, read_request(lease, 2))
    c.held = True
    with pytest.raises(Rejected, match="collection_authority_unavailable"):
        authorize_read(c.service, c.worker, read_request(lease, 3))
    c.held = False
    c.now += 20
    with pytest.raises(Rejected, match="stale_lease"):
        authorize_read(c.service, c.worker, read_request(lease, 3))


def test_vm_must_be_observed_in_datacenter_before_any_profile_read(campaign: Campaign) -> None:
    c = campaign
    install(c, True)
    lease = pending(c, listed=False)
    with pytest.raises(Rejected, match="vm_not_in_enrolled_scope"):
        authorize_read(c.service, c.worker, read_request(lease, 1))


def test_profiles_reviews_and_confirmations_survive_restart_and_reject_stale_scope(
    campaign: Campaign,
) -> None:
    c = campaign
    source, target = collected(c, True), collected(c, False)
    app = WorkloadProfiles(c.service)
    body, key = review(source, target), uid()
    saved = app.command(c.actor, "migration_save", body, key)
    assert app.command(c.actor, "migration_save", body, key) == saved
    with pytest.raises(Rejected, match="current_migration_review_required"):
        app.planning(c.actor.tenant, c.actor.site or "", 1, saved["digest"])
    app.command(c.actor, "migration_confirm", {"digest": saved["digest"]}, uid(), expected=1)
    restarted = WorkloadProfiles(c.service)
    result = restarted.planning(c.actor.tenant, c.actor.site or "", 1, saved["digest"])
    assert result["datasets"] == body["datasets"] and not result["native_write_authorized"]
    assert result["source"]["profile_sha256"] != result["target"]["profile_sha256"]
    with pytest.raises(Rejected, match="not_found"):
        app.command(replace(c.actor, tenant=uid()), "migration_save", body, uid())
    with pytest.raises(Rejected, match="action_denied"):
        app.read(replace(c.actor, action="inventory.read"))
    with pytest.raises(Rejected, match="stale_revision"):
        app.command(c.actor, "migration_save", body, uid(), expected=2)
    with c.database.transaction() as tx:
        assert row(tx, "SELECT count(*) AS n FROM inventory.workload_profiles")["n"] == 2
    for table in ("workload_profiles", "migration_reviews", "migration_confirmations"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with c.database.transaction() as tx:
                tx.execute("DELETE FROM inventory." + table)
    c.now += 400
    with pytest.raises(Rejected, match="current_migration_review_required"):
        restarted.planning(c.actor.tenant, c.actor.site or "", 1, saved["digest"])


def test_confirmed_review_can_pin_exact_catalogue_logical_workload() -> None:
    body = review(uid(), uid())
    binding = {
        "application_id": uid(), "environment_id": uid(),
        "revision_id": uid(), "workload_id": uid(), "intent_sha256": "1" * 64,
        "disk_mappings": [{"logical_device_id": uid(), "native_key": 2000}],
        "nic_mappings": [],
    }
    body["catalogue_binding"] = binding
    review_input(body, profile(1000))
    body["catalogue_binding"] = {**binding, "intent_sha256": "not-a-digest"}
    with pytest.raises(Rejected, match="invalid_profile_digest"):
        review_input(body, profile(1000))
    body["catalogue_binding"] = {**binding, "untrusted": True}
    with pytest.raises(Rejected, match="unknown_field"):
        review_input(body, profile(1000))


def test_catalogue_mapping_cannot_skip_or_duplicate_native_devices() -> None:
    body = review(uid(), uid())
    binding = {
        "application_id": uid(), "environment_id": uid(),
        "revision_id": uid(), "workload_id": uid(), "intent_sha256": "2" * 64,
        "disk_mappings": [{"logical_device_id": uid(), "native_key": 2000}],
        "nic_mappings": [],
    }
    body["catalogue_binding"] = binding
    review_input(body, profile(1000))
    for bad in ([], [{"logical_device_id": uid(), "native_key": 2001}],
                binding["disk_mappings"] * 2):
        body["catalogue_binding"] = {**binding, "disk_mappings": bad}
        with pytest.raises(Rejected, match="catalogue_native_device"):
            review_input(body, profile(1000))
