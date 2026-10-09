"""Installed feature-scoped native API contract. Namespaces do not imply support.

Mirrors contracts/capabilities/native-security-api-registry-v1.json. In
production the separate signed Assurance runtime check additionally pins
the exact installed API profile/release and individual endpoint receipts.
"""
from typing import Any

from planning.domain.model import digest

FEATURES = {
    ("vmware", "nsx-policy", "v1"): frozenset({
        "policy-order", "effective-applied-to", "group-effective-vm-members",
        "service-expansion", "native-default-action", "realized-revision",
        "native-route-nat", "active-flow-probes",
    }),
    ("ahv", "microseg", "v4.2"): frozenset({
        "policy-order", "effective-categories", "entity-membership",
        "service-expansion", "policy-attachments", "native-route-nat",
        "active-flow-probes",
    }),
    ("ahv", "microseg", "v4.3"): frozenset({
        "policy-order", "effective-categories", "entity-membership",
        "service-expansion", "policy-attachments", "native-route-nat",
        "active-flow-probes",
    }),
    ("openstack", "neutron", "v2.0"): frozenset({
        "security-group-port-attachments", "additive-ingress-egress",
        "remote-member-resolution", "statefulness", "ip-family",
        "native-route-nat", "active-flow-probes",
    }),
}


def qualify(document: dict[str, Any]) -> bool:
    profile = document.get("api_profile")
    if not isinstance(profile, dict):
        return False
    platform = document.get("platform")
    key = (platform, profile.get("namespace"), profile.get("api_version"))
    needed = FEATURES.get(key)
    installed = profile.get("installed")
    features = profile.get("qualified_features")
    if (needed is None or profile.get("verified") is not True
            or profile.get("observer") != document.get("observer_principal")
            or profile.get("environment_scope") != document.get("native_scope")
            or profile.get("profile_sha256") is None
            or not isinstance(installed, dict)
            or not isinstance(installed.get("version"), str)
            or not installed["version"]
            or not isinstance(installed.get("build"), str)
            or not installed["build"]
            or not isinstance(features, dict)
            or not needed.issubset(features)
            or any(features.get(name) != "qualified"
                   for name in needed)
            or not isinstance(profile.get("evidence_sha256"), str)
            or len(profile["evidence_sha256"]) != 64):
        return False
    # Per-feature qualification is tied to exact installed product/API and
    # owner-controlled native origin. An E2 probe reporting a 200 is NOT enough.
    expected = digest({
        "platform": platform, "namespace": key[1], "api_version": key[2],
        "installed": installed, "features": features,
        "environment_scope": profile["environment_scope"],
        "profile_sha256": profile["profile_sha256"],
        "native_origin_id": profile.get("native_origin_id"),
    })
    return expected == profile["evidence_sha256"]
