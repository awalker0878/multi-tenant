"""NSX Policy discovery is read-only, bounded, and never effective VM membership."""
import pytest

from inventory_worker.infrastructure import nsx_security
from inventory_worker.infrastructure.native import CollectionFailure


def test_nsx_priority_scopes_and_references_remain_e2(monkeypatch):
    calls = []
    permits = []
    group = "/infra/domains/d1/groups/app"
    service = "/infra/services/HTTPS"
    def exchange(stream, path, headers):
        calls.append(path)
        assert len(calls) == len(permits)
        assert stream["base_url"] == "https://nsx.enrolled.example"
        assert headers["Authorization"] == "Basic fixture"
        if path.endswith("/groups?page_size=100"):
            return {"results": [{"id": "app", "expression": [{"resource_type": "Condition"}]}]}
        if path.endswith("/services?page_size=100"):
            return {"results": [{"id": "HTTPS", "service_entries": [{"protocol": "TCP"}]}]}
        if path.endswith("/security-policies?page_size=100"):
            return {"results": [{
                "id": "app-security", "category": "Application", "stateful": True,
                "sequence_number": 20, "scope": [group],
            }]}
        return {"results": [{
            "id": "allow-web", "action": "ALLOW", "direction": "IN_OUT",
            "sequence_number": 10, "services": [service],
            "source_groups": [group], "destination_groups": [group],
            "_links": [{"href": "https://attacker.invalid"}],
        }]}
    monkeypatch.setattr(nsx_security, "exchange", exchange)
    monkeypatch.setattr(nsx_security, "secret", lambda _: "fixture")
    result = nsx_security.collect_nsx_policy_rules({
        "kind": "nsx_policy", "domain_id": "d1",
        "base_url": "https://nsx.enrolled.example",
        "credential_file": "/secure/fixture",
    }, "d1", lambda: permits.append(True))
    assert len(calls) == 4 and "attacker.invalid" not in str(calls)
    policy = result["policies"][0]
    assert policy["category"] == "Application"
    assert policy["sequence_number"] == 20
    assert policy["rules"][0]["services"] == [service]
    assert result["groups"][0]["resolution"] == "unverified"
    assert result["services"][0]["resolution"] == "unverified"
    assert "nsx_effective_membership_unverified" in result["holds"]
    assert result["semantic_qualification"] == "unresolved"
    assert result["native_write_authorized"] is False


def test_nsx_catalog_denies_wrong_domain_and_unbounded_pages(monkeypatch):
    stream = {"kind": "nsx_policy", "domain_id": "d1", "credential_file": "/fixture"}
    with pytest.raises(CollectionFailure):
        nsx_security.collect_nsx_policy_rules(stream, "d2", lambda: None)
    monkeypatch.setattr(nsx_security, "secret", lambda _: "fixture")
    monkeypatch.setattr(nsx_security, "exchange", lambda *args, **kw:
        {"cursor": "unapproved-next-page", "results": []})
    with pytest.raises(CollectionFailure):
        nsx_security.collect_nsx_policy_rules(stream, "d1", lambda: None)


def test_unknown_nsx_group_and_service_references_never_become_effective(monkeypatch):
    monkeypatch.setattr(nsx_security, "secret", lambda _: "fixture")
    def exchange(stream, path, headers):
        if path.endswith("/rules?page_size=100"):
            return {"results": [{
                "id": "rule1", "action": "ALLOW", "direction": "IN_OUT",
                "services": ["/infra/services/not-observed"],
            }]}
        if path.endswith("/security-policies?page_size=100"):
            return {"results": [{"id": "policy1"}]}
        return {"results": []}
    monkeypatch.setattr(nsx_security, "exchange", exchange)
    result = nsx_security.collect_nsx_policy_rules(
        {"kind": "nsx_policy", "domain_id": "d1", "credential_file": "/fixture"},
        "d1", lambda: None,
    )
    assert "nsx_native_rule_references_missing" in result["holds"]
    assert result["policies"][0]["rules"][0]["group_reference_status"] == "unresolved"
