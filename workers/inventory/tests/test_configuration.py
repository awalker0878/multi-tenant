"Controlled provider responses exercise projection and scope; not native E3 evidence."

import json
from typing import Any

import pytest

from inventory_worker.infrastructure.configuration import QUERIES, collect_configuration, normalized
from inventory_worker.infrastructure.generated_configuration_streams import configuration_streams
from inventory_worker.infrastructure.native import CollectionFailure


def test_version_discovery_keeps_ranges_and_discards_secrets() -> None:
    result = normalized(
        "compute_versions",
        {
            "versions": [
                {
                    "id": "v2.1",
                    "min_version": "2.1",
                    "version": "2.104",
                    "status": "CURRENT",
                    "password": "never-store",
                    "links": [],
                }
            ]
        },
        "p",
    )
    assert result[0]["id"] == "v2.1"
    assert "2.104" in json.dumps(result) and "never-store" not in json.dumps(result)
    assert normalized(
        "placement_versions", {"versions": [{"id": "v1.0", "max_version": "1.39"}]}, "p"
    )[0]["attributes"]


@pytest.mark.parametrize("query", list(QUERIES))
def test_missing_or_malformed_configuration_is_not_empty_success(query: str) -> None:
    with pytest.raises(CollectionFailure, match="invalid_response"):
        normalized(query, {}, "p")


def test_foreign_scope_and_continuations_are_held() -> None:
    with pytest.raises(CollectionFailure, match="permission_denied"):
        normalized("network_ports", {"ports": [{"id": "port", "project_id": "other"}]}, "p")
    with pytest.raises(CollectionFailure, match="invalid_response"):
        normalized(
            "network_ports",
            {"ports": [], "ports_links": [{"rel": "next", "href": "https://hostile"}]},
            "p",
        )
    with pytest.raises(CollectionFailure, match="invalid_response"):
        normalized("volume_types", {"volume_types": [{"id": str(i)} for i in range(100)]}, "p")


def test_installed_extensions_and_configured_policy_keep_different_evidence() -> None:
    assert (
        normalized(
            "network_extensions",
            {"extensions": [{"alias": "port-security", "name": "Port security"}]},
            "p",
        )[0]["id"]
        == "port-security"
    )
    result = normalized(
        "network_security_groups",
        {
            "security_groups": [
                {
                    "id": "sg",
                    "project_id": "p",
                    "security_group_rules": [{"direction": "ingress", "password": "never-store"}],
                }
            ]
        },
        "p",
    )
    assert "ingress" in json.dumps(result) and "never-store" not in json.dumps(result)


def test_core_queries_derive_only_from_trusted_bases_and_keep_explicit_overrides() -> None:
    streams = [
        {
            "kind": k,
            "base_url": base,
            "addresses": ["127.0.0.1"],
            "credential_file": "/token",
            "ca_file": "/ca",
            "api_version": "2.1",
        }
        for k, base in (
            ("server", "https://compute.example/nova/v2.1"),
            ("network", "https://network.example/v2.0"),
            ("volume", "https://volume.example/volume/v3/project-a"),
        )
    ]
    expanded = configuration_streams(streams, "openstack")
    assert len(expanded) == 15 and len(streams) == 3
    assert (
        next(x for x in expanded if x["kind"] == "config_compute_versions")["base_url"]
        == "https://compute.example/nova"
    )
    assert (
        next(x for x in expanded if x["kind"] == "config_volume_versions")["base_url"]
        == "https://volume.example/volume"
    )
    assert configuration_streams(expanded, "openstack") == expanded
    assert configuration_streams(streams, "vmware") == streams


def test_denied_pull_is_unknown_with_no_provider_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("inventory_worker.infrastructure.configuration.secret", lambda _: "token")

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise CollectionFailure("permission_denied")

    monkeypatch.setattr("inventory_worker.infrastructure.configuration.exchange", denied)
    result = collect_configuration(
        {"platform": "openstack", "native_scope": "p", "coverage_reference": "ref"},
        {
            "kind": "config_network_ports",
            "api_version": "discovery-v1",
            "credential_file": "/token",
        },
    )
    assert result["configuration"] == {
        "query": "network_ports",
        "status": "permission_denied",
        "items": [],
    }
    assert result["terminal"] is True and result["observations"] == []
