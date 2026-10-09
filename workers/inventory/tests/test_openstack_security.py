"""Scoped source and target Neutron allow/deny rule semantic comparisons."""
import pytest

from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.openstack_security import rule_choices, security_semantics

def rules(*, dest=False):
    return {
        "stateful": True,
        "security_group_rules": [{
            "id": "rule-other" if dest else "rule-source",
            "project_id": "project-b" if dest else "project-a",
            "security_group_id": "group-b" if dest else "group-a",
            "direction": "ingress",
            "ethertype": "IPv4",
            "protocol": "TCP" if dest else "tcp",
            "port_range_min": 443, "port_range_max": 443,
            "remote_ip_prefix": "10.0.0.4/24" if dest else "10.0.0.0/24",
            "remote_group_id": None,
        }],
    }

def test_rule_signature_ignores_native_ids_but_preserves_flow_semantics():
    assert security_semantics(rules()) == security_semantics(rules(dest=True))
    changed = rules(dest=True)
    changed["security_group_rules"][0]["port_range_min"] = 22
    assert security_semantics(rules()) != security_semantics(changed)
    changed["security_group_rules"][0]["port_range_min"] = 443
    changed["security_group_rules"][0]["direction"] = "egress"
    assert security_semantics(rules()) != security_semantics(changed)

def test_unknown_statefulness_and_native_remote_group_dependencies_cannot_match():
    changed = rules()
    changed.pop("stateful")
    assert security_semantics(changed) is None
    changed = rules()
    changed["security_group_rules"][0]["remote_group_id"] = "source-group"
    assert security_semantics(changed) is None

def test_invalid_natively_observed_rules_fail_closed():
    for fault in ("direction", "cidr", "port"):
        changed = rules()
        row = changed["security_group_rules"][0]
        if fault == "direction":
            row["direction"] = "any"
        elif fault == "cidr":
            row["remote_ip_prefix"] = "not-a-cidr"
        else:
            row["port_range_min"] = 99999
        with pytest.raises(CollectionFailure):
            security_semantics(changed)


def test_source_and_destination_rule_choices_are_exact_api_ids_not_free_text():
    source = rule_choices(rules())
    destination = rule_choices(rules(dest=True))
    assert source is not None and destination is not None
    assert source[0]["id"] == "rule-source"
    assert destination[0]["id"] == "rule-other"
    assert source[0]["semantic_sha256"] == destination[0]["semantic_sha256"]
    assert source[0]["remote_ip_prefix"] == "10.0.0.0/24"
    differing = rules(dest=True)
    differing["security_group_rules"][0]["port_range_max"] = 8443
    assert rule_choices(differing)[0]["semantic_sha256"] != source[0]["semantic_sha256"]


def test_unknown_group_references_do_not_generate_selectable_rules():
    unsafe = rules()
    unsafe["security_group_rules"][0]["remote_group_id"] = "other-group"
    assert rule_choices(unsafe) is None
    unknown = rules()
    unknown.pop("stateful")
    assert rule_choices(unknown) is None
