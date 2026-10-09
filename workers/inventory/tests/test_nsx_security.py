"""NSX Policy API is a separate enrolled native origin, not a vCenter shortcut."""
import pytest

from inventory_worker.infrastructure import nsx_security
from inventory_worker.infrastructure.native import CollectionFailure


def test_nsx_rule_catalogue_uses_enrolled_domain_and_never_follows_links(monkeypatch):
    calls = []
    permits = []
    def exchange(stream, path, headers):
        calls.append(path)
        assert len(calls) == len(permits)
        assert stream["base_url"] == "https://nsx.enrolled.example"
        assert headers["Authorization"] == "Basic fixture"
        if path.endswith("/rules?page_size=100"):
            return {"results": [{
                "id": "allow-web", "action": "ALLOW", "direction": "IN_OUT",
                "services": ["/infra/services/HTTPS"],
                "_links": [{"href": "https://attacker.invalid"}],
            }]}
        return {"results": [{"id": "app-security", "scope": ["/infra/domains/d1/groups/app"]}]}
    monkeypatch.setattr(nsx_security, "exchange", exchange)
    monkeypatch.setattr(nsx_security, "secret", lambda _: "fixture")
    result = nsx_security.collect_nsx_policy_rules({
        "kind": "nsx_policy", "domain_id": "d1",
        "base_url": "https://nsx.enrolled.example",
        "credential_file": "/secure/fixture",
    }, "d1", lambda: permits.append(True))
    assert len(calls) == 2 and "attacker.invalid" not in str(calls)
    rule = result["policies"][0]["rules"][0]
    assert rule["id"] == "allow-web"
    assert rule["service_reference_status"] == "unresolved"
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


def test_unqualified_nsx_rule_semantics_cannot_be_guessed(monkeypatch):
    monkeypatch.setattr(nsx_security, "secret", lambda _: "fixture")
    def exchange(stream, path, headers):
        if path.endswith("/rules?page_size=100"):
            return {"results": [{"id": "rule1", "action": "ALLOW", "direction": "IN_OUT"}]}
        return {"results": [{"id": "policy1"}]}
    monkeypatch.setattr(nsx_security, "exchange", exchange)
    result = nsx_security.collect_nsx_policy_rules(
        {"kind": "nsx_policy", "domain_id": "d1", "credential_file": "/fixture"},
        "d1", lambda: None,
    )
    assert result["policies"][0]["rules"][0]["group_reference_status"] == "unresolved"
