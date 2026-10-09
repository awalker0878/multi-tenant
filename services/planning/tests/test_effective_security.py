"""Effective security evidence is not native inventory; every unsupported gap holds."""
from copy import deepcopy

import pytest

from planning.domain.effective_security import qualify
from planning.domain.model import digest


NOW = 1000
FLOW = {"from": "app-web", "to": "app-db", "protocol": "tcp", "port": 5432}
DENIED = {"from": "unauthorized-peer", "to": "app-db", "protocol": "tcp", "port": 5432}


def proof(platform="vmware", nat=False):
    path = {
        "nodes": ["app-web", "transit", "app-db"], "scope": "scope-prod",
        "source_address": "192.0.2.10", "destination_address": "198.51.100.15",
        "multipath_resolved": True, "complete": True,
        "hops": [
            {
                "from": "app-web", "to": "transit",
                "native_ref": "route-to-edge", "scope": "scope-prod",
                "forward_observed": True, "reverse_observed": True,
                "nat": ({
                    "kind": "snat", "native_ref": "nat-1",
                    "before_source": "192.0.2.10",
                    "before_destination": "198.51.100.15",
                    "after_source": "203.0.113.14",
                    "after_destination": "198.51.100.15",
                    "before_port": 5432, "after_port": 5432,
                    "stateful_return_observed": True,
                } if nat else None),
            },
            {
                "from": "transit", "to": "app-db",
                "native_ref": "route-to-db", "scope": "scope-prod",
                "forward_observed": True, "reverse_observed": True,
            },
        ],
        "observed_egress_source": "203.0.113.14" if nat else "192.0.2.10",
        "observed_egress_destination": "198.51.100.15",
        "reverse_path_measured": True,
    }
    groups = {
        "source": {
            "resolution": "effective_native_members", "complete": True,
            "members": ["app-web"], "native_revision": "src-revision",
        },
        "destination": {
            "resolution": "effective_native_members", "complete": True,
            "members": ["app-db"], "native_revision": "dst-revision",
        },
    }
    services = {
        "postgres": {
            "resolution": "native_expanded", "complete": True,
            "protocol": "tcp", "ports": [5432], "native_revision": "svc-revision",
        }
    }
    rule = {
        "native_ref": "policy-application:rule-7", "category": "Application",
        "policy_sequence": 20, "priority": 10,
        "enabled": True, "effective_scope_qualified": True,
        "native_revision": "rule-revision", "action": "allow",
        "direction": "both", "stateful": True,
        "source_group": "source", "destination_group": "destination",
        "service_ref": "postgres", "policy_state": "ENFORCE",
    }
    if platform == "ahv":
        rule.pop("category")
        rule.pop("policy_sequence")
    result = {
        "schema_version": 1, "source": "independent_native_observer",
        "platform": platform, "observer_principal": "observer",
        "writer_principal": "native-writer",
        "observed_at": NOW, "expires_at": NOW + 45,
        "topology_sha256": "topo", "default_action": "deny",
        "default_deny_native_ref": "default-deny-prod",
        "effective_membership_observed": True,
        "groups": groups, "services": services, "rules": [rule],
        "path": path, "forbidden_flow": DENIED,
    }
    path_sha = digest(path)
    result["probes"] = [
        {
            **flow, "outcome": outcome, "observer": "observer",
            "native_receipt": "probe-" + outcome,
            "topology_sha256": "topo",
            "path_sha256": path_sha,
            "denied_at_native_ref": "default-deny-prod" if outcome == "deny" else None,
            "enforcement_scope": "scope-prod" if outcome == "deny" else None,
            "observed_at": NOW,
            "expires_at": NOW + 45,
        }
        for flow, outcome in ((FLOW, "allow"), (DENIED, "deny"))
    ]
    return result


@pytest.mark.parametrize("platform", ["vmware", "ahv", "openstack"])
@pytest.mark.parametrize("nat", [False, True])
def test_native_multihop_and_stateful_nat_need_independent_witness(platform, nat):
    d = proof(platform, nat)
    result = qualify(d, FLOW, NOW)
    assert result["status"] == "qualified"
    assert result["effective_rule_native_ref"] == d["rules"][0]["native_ref"]
    assert result["path_sha256"] == digest(d["path"])
    assert result["native_write_authorized"] is False


@pytest.mark.parametrize("change", [
    "precedence", "dynamic_membership", "unresolved_service", "higher_deny",
    "nat_return", "loop", "missing_hop", "unmeasured_negative", "stale",
    "writer_is_observer", "missing_return", "wrong_source",
])
def test_unknown_or_unsafe_native_behavior_fails_closed(change):
    d = proof("vmware", True)
    if change == "precedence":
        d["rules"].append({**d["rules"][0], "native_ref": "conflicting-rule"})
    elif change == "dynamic_membership":
        d["groups"]["source"]["resolution"] = "expression_only"
    elif change == "unresolved_service":
        d["services"]["postgres"]["complete"] = False
    elif change == "higher_deny":
        d["rules"].append({
            **d["rules"][0], "native_ref": "emergency-deny", "category": "Emergency",
            "priority": 1, "action": "deny",
        })
    elif change == "nat_return":
        d["path"]["hops"][0]["nat"]["stateful_return_observed"] = False
    elif change == "loop":
        d["path"]["nodes"] = ["app-web", "transit", "app-web"]
    elif change == "missing_hop":
        d["path"]["hops"] = d["path"]["hops"][:1]
    elif change == "unmeasured_negative":
        d["probes"] = d["probes"][:1]
    elif change == "stale":
        d["observed_at"] = NOW - 31
    elif change == "writer_is_observer":
        d["writer_principal"] = "observer"
    elif change == "missing_return":
        d["path"]["reverse_path_measured"] = False
    elif change == "wrong_source":
        d["groups"]["source"]["members"] = ["another-app"]
    assert qualify(d, FLOW, NOW)["status"] == "held"


def test_policy_order_denies_even_when_lower_priority_allow_exists():
    d = proof("ahv")
    d["rules"].append({
        **d["rules"][0], "native_ref": "higher-deny",
        "priority": 1, "action": "deny",
    })
    assert qualify(d, FLOW, NOW)["reason"] == "higher_priority_native_deny"


def test_nat_port_translation_must_match_native_egress_port():
    d = proof("vmware", True)
    d["path"]["hops"][0]["nat"]["after_port"] = 15432
    assert qualify(d, FLOW, NOW)["reason"] == "native_return_path_unqualified"
    d["path"]["observed_egress_port"] = 15432
    for row in d["probes"]:
        row["path_sha256"] = digest(d["path"])
    assert qualify(d, FLOW, NOW)["status"] == "qualified"


def test_untested_vrf_crossing_or_stateful_direction_fails_closed():
    d = proof("ahv", True)
    d["path"]["hops"][0]["next_scope"] = "scope-shared"
    assert qualify(d, FLOW, NOW)["reason"] == "native_nat_cross_scope_unqualified"
    d["path"]["hops"][0]["nat"]["cross_scope_authorized"] = True
    d["path"]["hops"][1]["scope"] = "scope-shared"
    d["path"]["destination_scope"] = "scope-shared"
    for row in d["probes"]:
        row["path_sha256"] = digest(d["path"])
    assert qualify(d, FLOW, NOW)["status"] == "qualified"
    d["rules"][0]["stateful"] = False
    assert qualify(d, FLOW, NOW)["reason"] == "native_security_return_state_unqualified"


def test_observer_must_report_a_distinct_negative_flow():
    d = proof()
    d["forbidden_flow"] = dict(FLOW)
    assert qualify(d, FLOW, NOW)["reason"] == "independent_negative_flow_missing"


def test_vendor_native_dropdown_requires_effective_source_and_target_not_e2_references():
    from planning.application.migration_flows import MigrationFlows
    source, destination = proof("vmware"), proof("ahv", nat=True)
    intent = {"dependencies": [{**FLOW, "kind": "communication", "strength": "required"}]}
    case = {
        "source_flow_id": digest(FLOW), "flow": FLOW,
        "source_document": source, "document": destination,
    }
    choices = MigrationFlows.qualified_native_choices(
        intent, "ahv", [case], NOW,
    )
    assert choices[0]["destination_firewall_rule_ids"] == [
        destination["rules"][0]["native_ref"]
    ]
    assert choices[0]["destination_route_ids"] == [
        "path:" + digest(destination["path"])
    ]
    assert choices[0]["native_write_authorized"] is False
    case["source_document"]["groups"]["source"]["resolution"] = "expression_only"
    from planning.domain.model import Rejected
    with pytest.raises(Rejected, match="native_source_security_"):
        MigrationFlows.qualified_native_choices(intent, "ahv", [case], NOW)
