"""Every profile GET requires a fresh per-request permit; no endpoint is taken from responses."""

from typing import Any

import pytest
from test_workload_profile import records

from inventory_worker.infrastructure import vmware_workload
from inventory_worker.infrastructure.native import CollectionFailure, collect
from inventory_worker.infrastructure.profile_collection import collect_profile


def test_profile_stream_without_current_request_authority_is_denied() -> None:
    with pytest.raises(CollectionFailure, match="permission_denied"):
        collect(
            {"platform": "vmware", "native_scope": "dc-1", "streams": [{"kind": "source_profile"}]},
            0,
            None,
        )


def test_revocation_between_vi_reads_stops_the_native_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[str] = []
    r = records()

    def exchange(stream: Any, path: str, headers: Any) -> Any:
        requests.append(path)
        return r["config"] if path.endswith("/config") else r["runtime"]

    def authority() -> None:
        if len(requests) == 2:
            raise CollectionFailure("permission_denied")

    monkeypatch.setattr(vmware_workload, "exchange", exchange)
    monkeypatch.setattr(vmware_workload, "secret", lambda _: "fixture")
    stream = {
        "kind": "source_profile",
        "vm_ids": ["vm-1"],
        "api_version": "9.1.1.0",
        "credential_file": "/fixture",
    }
    with pytest.raises(CollectionFailure, match="permission_denied"):
        collect_profile({"coverage_reference": "observer"}, stream, None, authority)
    assert [p.rsplit("/", 1)[1] for p in requests] == ["config", "runtime"]


def test_target_uses_enrolled_origins_and_observed_version_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from inventory_worker.infrastructure import profile_collection as module

    calls: list[tuple[str, str, bool]] = []
    permits: list[bool] = []
    policy: dict[str, Any] = {
        "platform": "openstack",
        "native_scope": "project-a",
        "coverage_reference": "observer",
        "streams": [
            {"kind": kind, "base_url": origin, "credential_file": "/fixture"}
            for kind, origin in (
                ("server", "https://compute.example/v2.1"),
                ("network", "https://network.example/v2.0"),
                ("volume", "https://volume.example/v3/project-a"),
            )
        ],
    }
    stream = {
        "kind": "target_profile",
        "base_url": "https://image.example/v2",
        "credential_file": "/fixture",
    }

    def exchange(connection: Any, route: str, headers: Any, *, version_discovery: bool) -> Any:
        calls.append((connection["base_url"], route, version_discovery))
        assert len(permits) == len(calls)
        if route == "/schemas/image":
            return {"properties": {"disk_format": {"enum": ["raw"]}}}
        if route == "/info/import":
            return {"import-methods": {"value": ["glance-direct"]}}
        if route == "/flavors/detail?limit=100":
            return {"flavors": []}
        if route == "/types?limit=100":
            return {"volume_types": []}
        if route == "/extensions":
            return {"extensions": []}
        version = "v2.1" if "compute" in connection["base_url"] else "v3.0"
        return {
            "versions": [
                {
                    "id": version,
                    "version": "2.100" if version == "v2.1" else "3.75",
                    "min_version": version[1:],
                    "links": [{"href": "https://untrusted.invalid"}],
                }
            ]
        }

    monkeypatch.setattr(module, "exchange", exchange)
    monkeypatch.setattr(module, "secret", lambda _: "fixture")
    result = collect_profile(policy, stream, None, lambda: permits.append(True))
    assert result["profile"]["disk_formats"] == ["raw"]
    assert calls[-2:] == [
        ("https://compute.example", "/", True),
        ("https://volume.example", "/", True),
    ]
    assert len(calls) == 7
