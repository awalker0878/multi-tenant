"""Read VMware destination resources under an enrolled datacenter scope."""

import re
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
    # Query read-only VI/JSON EnvironmentBrowser options for each observed
    # destination host. Never expose guessed guestId/vmx values to operators.
    # A host without a complete API response simply has no selectable values.
    # Bound the campaign: hosts beyond this limit require a smaller scope.
    guest_options_by_host: list[dict[str, Any]] = []
    if len(records["hosts"]) <= 16:
        for host in records["hosts"]:
            key = host["host"]
            if not re.fullmatch(r"host-[0-9]+", key):
                continue
            prefix = "/sdk/vim25/" + stream["api_version"] + "/"
            try:
                before_request()
                parent = exchange(stream, prefix + "HostSystem/" + key + "/parent", headers)
                if (
                    not isinstance(parent, dict)
                    or parent.get("type") not in {"ComputeResource", "ClusterComputeResource"}
                    or not isinstance(parent.get("value"), str)
                    or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", parent["value"])
                ):
                    continue
                before_request()
                browser = exchange(
                    stream, prefix + parent["type"] + "/" + parent["value"] + "/environmentBrowser",
                    headers,
                )
                if (
                    not isinstance(browser, dict)
                    or browser.get("type") != "EnvironmentBrowser"
                    or not isinstance(browser.get("value"), str)
                    or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", browser["value"])
                ):
                    continue
                before_request()
                option = exchange(
                    stream, prefix + "EnvironmentBrowser/" + browser["value"] + "/QueryConfigOption",
                    headers, method="POST", body={},
                )
                if not isinstance(option, dict):
                    continue
                guests = option.get("guestOSDescriptor")
                hardware = option.get("version")
                if (
                    not isinstance(guests, list) or not 1 <= len(guests) <= 128
                    or not isinstance(hardware, str)
                    or re.fullmatch(r"vmx-[0-9]{2}", hardware) is None
                ):
                    continue
                guest_ids = [
                    desc["id"] for desc in guests if isinstance(desc, dict)
                    and isinstance(desc.get("id"), str)
                    and re.fullmatch(r"[A-Za-z0-9_]{1,80}Guest", desc["id"])
                ]
                if guest_ids and len(guest_ids) == len(guests) and len(set(guest_ids)) == len(guest_ids):
                    guest_options_by_host.append({
                        "host": key, "guest_ids": sorted(guest_ids),
                        "hardware_versions": [hardware],
                        "native_sha256": fingerprint([parent, browser, option]),
                    })
            except CollectionFailure as error:
                # A refused/revoked native read cannot be interpreted as an
                # absent compatibility option. Stop the campaign immediately.
                if error.reason in {
                    "permission_denied", "transport_unavailable", "throttled",
                    "unsafe_destination",
                }:
                    raise
                # Explicitly missing method/unsupported data is not an
                # operator-definable value: this host offers no selection.
                continue
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
        "guest_options_by_host": guest_options_by_host,
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
