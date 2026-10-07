"""Bounded native profile reads through explicitly enrolled service origins."""

import time
from collections.abc import Callable
from typing import Any

from inventory_worker.infrastructure.generated_configuration_streams import configuration_streams
from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.workload_profile import VmwareWorkloadDiscovery, target_profile


def collect_profile(
    policy: dict[str, Any],
    stream: dict[str, Any],
    cursor: str | None,
    before_request: Callable[[], None],
) -> dict[str, Any]:
    started = time.time()
    next_cursor = None
    if stream["kind"] == "source_profile":
        vms = stream["vm_ids"]
        if cursor is not None and cursor not in vms:
            raise CollectionFailure("invalid_response")
        index = vms.index(cursor) + 1 if cursor is not None else 0
        if index >= len(vms):
            raise CollectionFailure("invalid_response")
        vm = vms[index]
        profile = VmwareWorkloadDiscovery(
            stream, set(vms), stream["api_version"], lambda: int(started), before_request
        ).collect(vm)
        if index + 1 < len(vms):
            next_cursor = vm
    else:
        if cursor is not None:
            raise CollectionFailure("invalid_response")
        by_kind = {s["kind"]: s for s in configuration_streams(policy["streams"], "openstack")}
        if not {"config_compute_versions", "config_volume_versions"} <= by_kind.keys():
            raise CollectionFailure("unsupported_api")
        records = {}
        queries = (
            ("image_schema", stream, "/schemas/image"),
            ("image_import", stream, "/info/import"),
            ("flavors", by_kind["server"], "/flavors/detail?limit=100"),
            ("volume_types", by_kind["volume"], "/types?limit=100"),
            ("network_extensions", by_kind["network"], "/extensions"),
            ("compute_version", by_kind["config_compute_versions"], "/"),
            ("volume_version", by_kind["config_volume_versions"], "/"),
        )
        for key, connection, route in queries:
            before_request()
            headers = {"X-Auth-Token": secret(connection["credential_file"])}
            if key == "flavors":
                headers["OpenStack-API-Version"] = "compute 2.1"
            if key == "volume_types":
                headers["OpenStack-API-Version"] = "volume 3.0"
            result = exchange(
                connection, route, headers, version_discovery=key.endswith("_version")
            )
            if not isinstance(result, dict):
                raise CollectionFailure("invalid_response")
            if key.endswith("_version"):
                rows = result.get("versions", [result.get("version")])
                if isinstance(rows, dict):
                    rows = rows.get("values")
                if not isinstance(rows, list):
                    raise CollectionFailure("invalid_response")
                expected_id = "v2.1" if key == "compute_version" else "v3.0"
                matches = [r for r in rows if isinstance(r, dict) and r.get("id") == expected_id]
                if len(matches) != 1:
                    raise CollectionFailure("invalid_response")
                result = matches[0]
                if (
                    not isinstance(result, dict)
                    or not isinstance(result.get("version"), str)
                    or not isinstance(result.get("min_version"), str)
                ):
                    raise CollectionFailure("invalid_response")
            records[key] = result
        profile = target_profile(policy["native_scope"], records, int(started))
    return {
        "observations": [],
        "profile": profile,
        "next_cursor": next_cursor,
        "terminal": next_cursor is None,
        "coverage": policy["coverage_reference"] is not None,
        "collected_at": started,
        "error": None,
    }
