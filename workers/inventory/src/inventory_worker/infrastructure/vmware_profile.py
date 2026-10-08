"""Read VMware destination resources under an enrolled datacenter scope."""

from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.profile_digest import fingerprint


def collect_vmware(
    policy: dict[str, Any],
    stream: dict[str, Any],
    observed_at: int,
    before_request: Callable[[], None],
) -> dict[str, Any]:
    records: dict[str, Any] = {}
    headers = {"vmware-api-session-id": secret(stream["credential_file"])}
    before_request()
    content = exchange(
        stream,
        "/sdk/vim25/" + stream["api_version"] + "/ServiceInstance/ServiceInstance/content",
        headers,
    )
    if not isinstance(content, dict) or not isinstance(content.get("about"), dict):
        raise CollectionFailure("invalid_response")
    about = content["about"]
    if not all(
        isinstance(about.get(k), str) and about[k]
        for k in ("instanceUuid", "version", "apiVersion", "build")
    ):
        raise CollectionFailure("invalid_response")
    for plural, singular in (
        ("folders", "folder"),
        ("resource_pools", "resource-pool"),
        ("hosts", "host"),
        ("datastores", "datastore"),
        ("networks", "network"),
    ):
        before_request()
        rows = exchange(
            stream,
            "/api/vcenter/" + singular + "?" + urlencode({"datacenters": policy["native_scope"]}),
            headers,
        )
        key = singular.replace("-", "_")
        if (
            not isinstance(rows, list)
            or len(rows) > 100
            or any(not isinstance(r, dict) or not isinstance(r.get(key), str) for r in rows)
            or len({r[key] for r in rows}) != len(rows)
        ):
            raise CollectionFailure("invalid_response")
        if plural == "folders":
            # vCenter returns datacenter, host, network and datastore folders too.
            # Only the VM folder hierarchy can receive an imported workload.
            rows = [row for row in rows if row.get("type") == "VIRTUAL_MACHINE"]
        records[plural] = [
            {
                key: r[key],
                "name": r.get("name", r[key]),
                "type": r.get("type"),
                "native_sha256": fingerprint(r),
            }
            for r in rows
        ]
    return {
        "schema_version": 3,
        "profile_type": "TargetCapabilityProfile",
        "platform": "vmware",
        "project_id": policy["native_scope"],
        "vcenter_uuid": about["instanceUuid"],
        "api_version": stream["api_version"],
        "installed": about,
        "observed_at": observed_at,
        "observations_sha256": fingerprint([about, records]),
        "inventory_complete": True,
        "disk_formats": ["vmdk"],
        "image_import_methods": ["vi-json-nfc"],
        **records,
        "required_capability_evidence": [
            "guest_boot_drivers",
            "security_allow_and_deny",
            "service_validation",
            "recovery_and_cleanup",
            "nfc_tls_and_reachability",
        ],
        "holds": [] if all(records.values()) else ["vmware_destination_resources_incomplete"],
        "native_qualification": "not_established",
    }
