"""Provider-specific E4 rule, attachment, policy-boundary and packet-path contracts."""
from copy import deepcopy

import pytest

from planning.domain.model import digest
from planning.domain.policy_resolvers import Unqualified, decision
from planning.domain.effective_security import qualify
from planning.domain.security_boundary import compare

NOW = 1000
REQUIRED = {"from": "web", "to": "db", "protocol": "tcp", "port": 5432}
FORBIDDEN = {"from": "untrusted", "to": "db", "protocol": "tcp", "port": 5432}
EXTRA = {"from": "web", "to": "db", "protocol": "tcp", "port": 22}
FLOWS = (REQUIRED, FORBIDDEN, EXTRA)


def document(platform="vmware", generation="source", nat=False, multipath=False):
    groups = {
        "grp-web": {"resolution": "effective_native_members", "complete": True,
                    "native_revision": "gr-web", "members": ["vm-web"]},
        "grp-db": {"resolution": "effective_native_members", "complete": True,
                   "native_revision": "gr-db", "members": ["vm-db"]},
        "grp-untrusted": {"resolution": "effective_native_members", "complete": True,
                          "native_revision": "gr-x", "members": ["vm-x"]},
    }
    services = {
        "postgres": {"resolution": "native_expanded", "complete": True,
                     "native_revision": "service-v1", "protocol": "tcp", "ports": [5432]},
    }
    workloads = {}
    for logical, native, ip, port in (
        ("web", "vm-web", "192.0.2.10", "port-web"),
        ("db", "vm-db", "192.0.2.20", "port-db"),
        ("untrusted", "vm-x", "192.0.2.30", "port-x"),
    ):
        workloads[logical] = {
            "complete": True, "observed_by": "security-observer",
            "native_vm_id": native, "ips": [ip], "port_id": port,
            "attachment_revision": "attached-" + logical, "tenant_id": "tenant-1",
        }
    common = {
        "native_ref": "rule-allow-postgres", "action": "allow",
        "direction": "both", "enabled": True, "stateful": True,
        "effective_scope_qualified": True, "native_revision": "rule-v1",
        "source_group": "grp-web", "destination_group": "grp-db",
        "service_ref": "postgres",
    }
    rules = []
    if platform == "vmware":
        rules = [{
            **common, "category": "Application", "policy_sequence": 20, "priority": 1,
            "policy_applied_to": ["grp-db"], "rule_applied_to": ["grp-web"],
            "scope_precedence_verified": True,
        }]
    elif platform == "ahv":
        rules = [{
            **common, "policy_type": "application", "policy_state": "ENFORCE",
            "effective_priority": 20,
            "attached_vm_ids": ["vm-web", "vm-db"], "attachment_observed": True,
        }]
    else:
        rules = [{
            "native_ref": "neutron-egress", "action": "allow",
            "security_group_id": "sg-web", "direction": "egress",
            "ethertype": "ipv4", "protocol": "tcp",
            "port_range_min": 5432, "port_range_max": 5432,
            "effective_remote_vm_ids": ["vm-db"], "remote_scope_complete": True,
        }, {
            "native_ref": "neutron-ingress", "action": "allow",
            "security_group_id": "sg-db", "direction": "ingress",
            "ethertype": "ipv4", "protocol": "tcp",
            "port_range_min": 5432, "port_range_max": 5432,
            "effective_remote_vm_ids": ["vm-web"], "remote_scope_complete": True,
        }]
    doc = {
        "schema_version": 2, "source": "independent_native_observer",
        "platform": platform, "native_api_qualified": True,
        "native_scope": "tenant-prod", "tenant_id": "tenant-1",
        "enforcement_layer": "dfw",
        "firewall_chain_complete": True, "effective_firewall_layers": ["dfw"],
        "microseg_policy_priority_qualified": True,
        "policy_types_complete": True,
        "policy_exceptions_qualified": True,
        "quarantine_and_isolation_qualified": True,
        "built_in_sg_rules_observed": True,
        "anti_spoof_behavior_qualified": True,
        "address_family": "ipv4",
        "observer_principal": "security-observer", "writer_principal": "network-writer",
        "observed_at": NOW, "expires_at": NOW + 45,
        "topology_sha256": "topology-current",
        "default_action": "deny", "default_deny_native_ref": "default-deny",
        "effective_membership_observed": True, "rules_complete": True,
        "groups": groups, "services": services, "workloads": workloads,
        "rules": rules,
        "ports": {
            port: {"port_security_enabled": True, "project_id": "tenant-1",
                   "security_groups": [sg], "attached_groups_observed": True,
                   "native_revision": "port-version"}
            for port, sg in (
                ("port-web", "sg-web"), ("port-db", "sg-db"), ("port-x", "sg-x"),
            )
        },
        "security_groups": {
            sg: {"stateful": True, "complete": True}
            for sg in ("sg-web", "sg-db", "sg-x")
        },
    }
    from planning.domain.native_security_api import FEATURES
    namespace, api_version = {
        "vmware": ("nsx-policy", "v1"),
        "ahv": ("microseg", "v4.3"),
        "openstack": ("neutron", "v2.0"),
    }[platform]
    profile = {
        "namespace": namespace, "api_version": api_version,
        "installed": {"version": api_version, "build": generation + "-installed"},
        "qualified_features": {
            name: "qualified" for name in sorted(FEATURES[(platform, namespace, api_version)])
        },
        "observer": "security-observer", "environment_scope": "tenant-prod",
        "profile_sha256": "1" * 64 if generation == "source" else "2" * 64,
        "native_origin_id": "origin-" + generation, "verified": True,
    }
    profile["evidence_sha256"] = digest({
        "platform": platform, "namespace": namespace, "api_version": api_version,
        "installed": profile["installed"],
        "features": profile["qualified_features"],
        "environment_scope": profile["environment_scope"],
        "profile_sha256": profile["profile_sha256"],
        "native_origin_id": profile["native_origin_id"],
    })
    doc["api_profile"] = profile
    initial = {
        "source_ip": "192.0.2.10", "destination_ip": "192.0.2.20",
        "source_port": 50000, "destination_port": 5432,
        "protocol": "tcp", "address_family": "ipv4", "scope": "tenant-prod",
    }
    translated = dict(initial)
    if nat:
        translated["source_ip"] = "198.51.100.10"
        translated["source_port"] = 40000
    first = {
        "from": "web", "to": "router", "native_ref": "hop-web-router",
        "forward_observed": True, "reverse_observed": True,
        "policy_route_evaluated": True,
        "ingress_packet": initial, "egress_packet": translated,
        "nat": ({
            "type": "pat", "native_ref": "native-pat-1",
            "before": initial, "after": translated,
            "reverse_binding_observed": True,
        } if nat else None),
    }
    second = {
        "from": "router", "to": "db", "native_ref": "hop-router-db",
        "forward_observed": True, "reverse_observed": True,
        "policy_route_evaluated": True,
        "ingress_packet": translated, "egress_packet": translated,
    }
    path = {
        "id": "route-one", "routing_generation_id": "routes-v1",
        "complete": True, "nodes": ["web", "router", "db"],
        "ingress_packet": initial, "hops": [first, second],
        "egress_packet": translated, "reverse_path_measured": True,
    }
    doc["paths"] = [path]
    if multipath:
        alternate = deepcopy(path)
        alternate["id"] = "route-two"
        alternate["hops"][0]["native_ref"] = "hop-web-router-alt"
        alternate["hops"][1]["native_ref"] = "hop-router-db-alt"
        doc["paths"].append(alternate)
    doc["all_paths_observed"] = True
    doc["routing_generation_id"] = "routes-v1"
    doc["path_set_sha256"] = digest(sorted(digest(p) for p in doc["paths"]))
    doc["path_probes"] = {
        p["id"]: {
            "path_sha256": digest(p), "forward": "allow", "reverse": "allow",
            "observer": "security-observer",
            "native_receipt": p["id"] + "-signed-receipt",
            "observed_at": NOW, "expires_at": NOW + 45,
        } for p in doc["paths"]
    }
    doc["boundary_scope"] = {
        "complete": True, "workload_set_sha256": "f" * 64,
        "native_revision": "qualified-rules-" + generation,
        "generation_id": generation,
        "unrestricted_wildcards": False, "effective_rule_universe_complete": True,
        "address_families": ["ipv4", "ipv6"],
    }
    doc["boundary_probes"] = {}
    for f in FLOWS:
        verdict, _ = decision(doc, f)
        doc["boundary_probes"][digest(f)] = {
            "flow_sha256": digest(f), "outcome": verdict,
            "native_receipt": generation + "-" + digest(f),
            "observer": "security-observer",
            "native_revision": doc["boundary_scope"]["native_revision"],
            "observed_at": NOW, "expires_at": NOW + 45,
        }
    return doc


def boundary():
    return {
        "schema_version": 1, "complete": True, "workload_set_sha256": "f" * 64,
        "classes": [
            {"id": digest(flow), "flow": flow,
             "requirement": requirement}
            for flow, requirement in (
                (REQUIRED, "required"), (FORBIDDEN, "forbidden"), (EXTRA, "observed"),
            )
        ],
    }


@pytest.mark.parametrize("platform", ["vmware", "ahv", "openstack"])
@pytest.mark.parametrize("nat", [False, True])
def test_provider_effective_policy_and_full_nat_path(platform, nat):
    doc = document(platform, nat=nat, multipath=True)
    assert decision(doc, REQUIRED)[0] == "allow"
    assert decision(doc, FORBIDDEN)[0] == "deny"
    result = qualify(doc, REQUIRED, NOW)
    assert result["status"] == "qualified"
    assert result["path_sha256"] == doc["path_set_sha256"]
    assert len(result["native_route_refs"]) == 4
    assert result["native_write_authorized"] is False


@pytest.mark.parametrize("source,target", [
    ("vmware", "ahv"), ("ahv", "vmware"), ("openstack", "ahv"),
    ("vmware", "openstack"), ("openstack", "vmware"), ("ahv", "openstack"),
])
def test_complete_source_destination_security_boundary(source, target):
    src, dst = document(source, "source"), document(target, "destination")
    result = compare(src, dst, boundary(), NOW)
    assert result["status"] == "qualified"
    assert digest(REQUIRED) in result["allowed"]
    assert digest(FORBIDDEN) in result["denied"]


def test_neutron_is_additive_not_first_match():
    doc = document("openstack")
    doc["rules"].insert(0, {
        "native_ref": "another-group-ingress-rule", "action": "allow",
        "security_group_id": "sg-unattached", "direction": "ingress",
        "ethertype": "ipv4", "protocol": "tcp",
        "port_range_min": 1, "port_range_max": 65535,
        "effective_remote_vm_ids": ["vm-web"], "remote_scope_complete": True,
    })
    assert decision(doc, REQUIRED)[0] == "allow"
    doc["ports"]["port-db"]["security_groups"] = ["sg-unattached"]
    doc["security_groups"]["sg-unattached"] = {"stateful": True, "complete": True}
    assert decision(doc, REQUIRED)[0] == "allow"
    doc["ports"]["port-db"]["port_security_enabled"] = False
    with pytest.raises(Unqualified, match="neutron_port_attachment_unqualified"):
        decision(doc, REQUIRED)


def test_destination_must_not_add_access_not_permitted_by_source():
    src, dst = document("vmware", "source"), document("ahv", "destination")
    dst["services"]["ssh"] = {
        "resolution": "native_expanded", "complete": True,
        "native_revision": "new-service", "protocol": "tcp", "ports": [22],
    }
    dst["rules"].append({
        **dst["rules"][0], "native_ref": "excessive-ssh", "effective_priority": 30,
        "service_ref": "ssh",
    })
    dst["boundary_probes"][digest(EXTRA)]["outcome"] = "allow"
    result = compare(src, dst, boundary(), NOW)
    assert result["reason"] == "destination_additional_access_detected"


@pytest.mark.parametrize("fault", [
    "invalid_nsx_scope", "wrong_ahv_priority", "unobserved_members",
    "stale_probe", "missing_ecmp_path", "nat_not_reversible",
    "unknown_workload", "partial_boundary", "neutron_port_security_off",
])
def test_unknown_provider_or_path_evidence_never_qualifies(fault):
    src, dst = document("vmware", "source"), document("ahv", "destination", nat=True, multipath=True)
    if fault == "invalid_nsx_scope":
        src["rules"][0]["scope_precedence_verified"] = False
    elif fault == "wrong_ahv_priority":
        dst["microseg_policy_priority_qualified"] = False
    elif fault == "unobserved_members":
        src["groups"]["grp-db"]["resolution"] = "definition_only"
    elif fault == "stale_probe":
        dst["boundary_probes"][digest(REQUIRED)]["observed_at"] = NOW - 31
    elif fault == "missing_ecmp_path":
        dst["path_probes"].pop("route-two")
    elif fault == "nat_not_reversible":
        dst["paths"][0]["hops"][0]["nat"]["reverse_binding_observed"] = False
    elif fault == "unknown_workload":
        src["workloads"]["web"]["complete"] = False
    elif fault == "partial_boundary":
        src["boundary_scope"]["complete"] = False
    else:
        dst["ports"]["port-web"]["port_security_enabled"] = False
        dst["platform"] = "openstack"
    assert (qualify(src, REQUIRED, NOW)["status"] == "held"
            or qualify(dst, REQUIRED, NOW)["status"] == "held"
            or compare(src, dst, boundary(), NOW)["status"] == "held")


def test_legacy_generic_e4_claim_fails_closed():
    assert qualify({"schema_version": 1}, REQUIRED, NOW)["status"] == "held"


def test_optional_dependencies_can_be_offered_for_explicit_waiver():
    from planning.application.migration_flows import MigrationFlows
    src, dst = document("vmware", "source"), document("ahv", "destination")
    flow_id = digest(REQUIRED)
    intent = {"dependencies": [
        {**REQUIRED, "kind": "communication", "strength": "required"},
        {**EXTRA, "kind": "communication", "strength": "optional"},
    ]}
    cases = [{
        "source_flow_id": flow_id, "flow": REQUIRED,
        "source_document": src, "document": dst, "boundary": boundary(),
    }]
    choices = MigrationFlows.qualified_native_choices(
        intent, "ahv", cases, NOW, {"forbidden_flows": [FORBIDDEN]}, "tenant-prod",
    )
    assert choices[0]["status"] == "choices_observed"
    assert choices[1]["required"] is False
    assert choices[1]["status"] == "held_optional"
    assert choices[1]["destination_firewall_rule_ids"] == []


def test_short_lived_probe_refresh_does_not_change_reviewed_native_semantics():
    from planning.domain.effective_security import semantic_security_digest
    current = document("ahv", "destination")
    renewed = deepcopy(current)
    renewed["observed_at"] += 5
    renewed["expires_at"] += 5
    for proof in renewed["path_probes"].values():
        proof["observed_at"] += 5
        proof["expires_at"] += 5
    for proof in renewed["boundary_probes"].values():
        proof["observed_at"] += 5
        proof["expires_at"] += 5
    assert semantic_security_digest(renewed) == semantic_security_digest(current)
    renewed["rules"][0]["action"] = "deny"
    assert semantic_security_digest(renewed) != semantic_security_digest(current)


def test_unqualified_bypass_rules_and_second_firewall_layer_are_held():
    for platform, property_name in (
        ("vmware", "firewall_chain_complete"),
        ("ahv", "policy_exceptions_qualified"),
        ("openstack", "anti_spoof_behavior_qualified"),
    ):
        d = document(platform)
        d[property_name] = False
        assert qualify(d, REQUIRED, NOW)["status"] == "held"


def test_nutanix_installed_microseg_api_version_is_feature_qualified():
    doc = document("ahv")
    p = doc["api_profile"]
    p["api_version"] = "v4.2"
    p["installed"]["version"] = "v4.2"
    p["evidence_sha256"] = digest({
        "platform": "ahv", "namespace": "microseg", "api_version": "v4.2",
        "installed": p["installed"], "features": p["qualified_features"],
        "environment_scope": p["environment_scope"],
        "profile_sha256": p["profile_sha256"],
        "native_origin_id": p["native_origin_id"],
    })
    assert decision(doc, REQUIRED)[0] == "allow"
    p["qualified_features"]["effective-categories"] = "unknown"
    with pytest.raises(Unqualified, match="installed_native_api_features_unqualified"):
        decision(doc, REQUIRED)
