"""Explicitly synthetic owner responses; an E3 field tests matching, not native evidence."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from planning.domain.assessment import assess, requirements
from planning.domain.model import ACTIONS, DIMENSIONS, digest, profile

NOW = 2_000_000_000
TENANT = "10000000-0000-4000-8000-000000000001"
ACTOR = "10000000-0000-4000-8000-000000000002"
APP = "10000000-0000-4000-8000-000000000003"
ENV = "00000000-0000-4000-8000-000000000010"
SITE = "10000000-0000-4000-8000-000000000004"
ENDPOINT = "10000000-0000-4000-8000-000000000005"
GENERATION = "10000000-0000-4000-8000-000000000006"
REVISION = "10000000-0000-4000-8000-000000000007"


def inputs() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    intent = json.loads(
        (Path(__file__).resolve().parent / "fixtures/permit-desk-v1.json").read_text()
    )
    for w in intent["workloads"]:
        w["requirements"] = []
    p = profile(
        "openstack",
        "synthetic-v1",
        {d: {"status": "declared", "operations": list(ACTIONS)} for d in DIMENSIONS},
    )
    artifacts = {
        key: digest({"fixture": key}) for key in ("compiler", "adapter", "automation", "contracts")
    }
    policy = {
        "id": "synthetic-policy",
        "version": 1,
        "expires_at": NOW + 3600,
        "requirements": [],
        "artifacts": artifacts,
        "downtime_seconds": 3600,
        "reservation_owners": {
            k: "synthetic-" + k for k in ("vcpus", "memory_mib", "storage_gib", "addresses")
        },
        "terraform": {
            "saved_plan_sha256": digest("saved"),
            "toolchain_sha256": digest("tool"),
            "backend_ref": "fixture://state",
            "workspace": "fixture",
            "state_lineage": "lineage",
            "state_serial": 1,
            "lock_owner": "lifecycle",
        },
        "ownership": [
            {
                "resource": w["id"],
                "fields": ["infrastructure"],
                "writer": "terraform",
                "state_ref": "fixture://state",
                "native_identity": None,
            }
            for w in intent["workloads"]
        ],
    }
    req = requirements(intent) + [
        {"key": k, "value": True}
        for k in ("sovereignty.location", "sovereignty.custody", "sovereignty.data_path")
    ]
    capabilities: dict[str, Any] = {}
    for r in req:
        cap = capabilities.setdefault(
            r["key"],
            {"status": "observed", "values": [], "expires_at": NOW + 1800, "dependencies": []},
        )
        if r["value"] not in cap["values"]:
            cap["values"].append(r["value"])
    d = {
        "tenant_id": TENANT,
        "site_id": SITE,
        "endpoint_id": ENDPOINT,
        "generation_id": GENERATION,
        "platform": "openstack",
        "native_scope": "project:synthetic",
        "current": True,
        "completion": "complete",
        "expires_at": NOW + 1800,
        "holds": [],
        "installed_provenance": "observed",
        "installed_tuple": {
            "platform": "openstack",
            "release": "synthetic",
            "compute_api": "2.1",
            "network_api": "2.0",
            "storage_api": "3",
            "network_backend": "synthetic",
            "storage_backend": "synthetic",
            "guest": "synthetic",
        },
        "dimensions": {d: "observed" for d in DIMENSIONS},
        "capabilities": capabilities,
        "capacity": {"vcpus": 4, "memory_mib": 8192, "storage_gib": 80, "addresses": 2},
        "domain_bindings": {
            w["security_domain"]["id"]: "synthetic-domain-" + str(i)
            for i, w in enumerate(intent["workloads"])
        },
        "workload_bindings": {},
    }
    q: dict[str, Any] = {
        "id": "synthetic-evidence",
        "version": 1,
        "status": "qualified",
        "evidence_level": "E3",
        "expires_at": NOW + 1800,
        "revoked": False,
        "scope": {
            k: d[k]
            for k in ("tenant_id", "site_id", "endpoint_id", "native_scope", "installed_tuple")
        },
        "evidence_refs": ["fixture://not-native-evidence"],
        "dimensions": list(DIMENSIONS),
        "capabilities": deepcopy(capabilities),
    }
    q["scope"].update(
        action="application.provision",
        method="saved_plan",
        profile_digest=p["digest"],
        artifacts=artifacts,
    )
    for capability in q["capabilities"].values():
        capability["status"] = "supported"
    return intent, d, p, policy, q


def assessment() -> dict[str, Any]:
    intent, d, p, policy, q = inputs()
    return {
        "id": REVISION,
        "tenant_id": TENANT,
        "application_id": APP,
        "environment": ENV,
        "created_at": NOW,
        "action": "application.provision",
        "method": "saved_plan",
        "intent": {
            "id": REVISION,
            "application_id": APP,
            "intent": intent,
            "digest": digest(intent),
        },
        "inputs": [{"destination": d, "profile": p, "policy": policy, "qualification": q}],
        "results": [assess(intent, d, p, policy, q, "application.provision", "saved_plan", NOW)],
    }


def request() -> dict[str, Any]:
    return {
        "action": "application.provision",
        "method": "saved_plan",
        "lane": "operational",
        "executor_ids": [ACTOR],
        "valid_until": NOW + 300,
    }
