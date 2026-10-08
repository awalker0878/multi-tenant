"""Explicitly synthetic owner responses; an E3 field tests matching, not native evidence."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from planning.domain.assessment import assess, requirements
from planning.domain.capability_definitions import DEFINITION_SHA256
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
        "allowed_zones": ["zone-1"],
        "reservation_owners": {
            k: "synthetic-" + k for k in ("vcpus", "memory_mib", "storage_gib", "addresses")
        },
        "ownership": [
            {
                "resource": w["id"],
                "fields": ["infrastructure"],
                "writer": "lifecycle",
                "custody_ref": "evidence://fixture/custody",
                "native_identity": None,
            }
            for w in intent["workloads"]
        ],
    }
    project = "10000000-0000-4000-8000-000000000020"
    custody = "10000000-0000-4000-8000-000000000021"
    resources = []
    for index, _workload in enumerate(intent["workloads"]):
        prefix = "workload" + str(index)
        resources.extend(
            [
                {
                    "key": prefix + "_port",
                    "kind": "port",
                    "spec": {
                        "name": prefix + "-port",
                        "network_id": SITE,
                        "security_groups": [ENDPOINT],
                        "fixed_ips": [
                            {"subnet_id": GENERATION, "ip_address": "192.0.2." + str(index + 10)}
                        ],
                        "admin_state_up": False,
                        "port_security_enabled": True,
                    },
                },
                {
                    "key": prefix + "_boot",
                    "kind": "volume",
                    "spec": {
                        "name": prefix + "-boot",
                        "size": 40,
                        "volume_type": "qualified",
                        "availability_zone": "nova",
                        "imageRef": REVISION,
                    },
                },
                {
                    "key": prefix + "_vm",
                    "kind": "server",
                    "spec": {
                        "name": prefix + "-vm",
                        "flavorRef": "2",
                        "availability_zone": "nova",
                        "config_drive": True,
                        "ports": [prefix + "_port"],
                        "volumes": [{"key": prefix + "_boot", "boot_index": 0}],
                    },
                },
            ]
        )
    operation_plan = {
        "schema_version": 1,
        "project_id": project,
        "ownership_digest": digest(policy["ownership"]),
        "custody_id": custody,
        "custody_generation": 1,
        "api_versions": {"compute": "2.1", "network": "2.0", "volume": "3.0"},
        "resources": resources,
    }
    policy["native_api"] = {
        "operation_plan": operation_plan,
        "operation_plan_sha256": digest(operation_plan),
        "api_contracts_sha256": artifacts["contracts"],
        "adapter_sha256": artifacts["adapter"],
        "custody_ref": "evidence://fixture/custody",
        "custody_id": custody,
        "custody_generation": 1,
        "fence_owner": "lifecycle",
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
        "native_scope": "project:" + project,
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
        "version": 2,
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
        method="native_api",
        profile_digest=p["digest"],
        artifacts=artifacts,
    )
    for capability in q["capabilities"].values():
        capability["status"] = "supported"
    verify_fixture(q)
    d["capability_snapshot"] = snapshot_fixture(intent, d, policy, q)
    return intent, d, p, policy, q


def verify_fixture(record: dict[str, Any], now: int = NOW) -> None:
    """Synthetic authenticated owner boundary; never used by a production resolver."""
    record.pop("verification", None)
    checksum = digest(record)
    record["verification"] = {
        "valid": True,
        "definition_sha256": DEFINITION_SHA256,
        "decision_sha256": "a" * 64,
        "runtime_sha256": "b" * 64,
        "record_sha256": checksum,
        "resolved_at": now,
        "expires_at": record["expires_at"],
    }


def assessment() -> dict[str, Any]:
    intent, d, p, policy, q = inputs()
    return {
        "id": REVISION,
        "tenant_id": TENANT,
        "application_id": APP,
        "environment": ENV,
        "created_at": NOW,
        "action": "application.provision",
        "method": "native_api",
        "intent": {
            "id": REVISION,
            "application_id": APP,
            "intent": intent,
            "digest": digest(intent),
        },
        "inputs": [{"destination": d, "profile": p, "policy": policy, "qualification": q}],
        "results": [assess(intent, d, p, policy, q, "application.provision", "native_api", NOW)],
    }


def request() -> dict[str, Any]:
    return {
        "action": "application.provision",
        "method": "native_api",
        "lane": "operational",
        "executor_ids": [ACTOR],
        "valid_until": NOW + 300,
    }


def snapshot_fixture(
    intent: dict[str, Any], destination: dict[str, Any], policy: dict[str, Any], q: dict[str, Any]
) -> dict[str, Any]:
    pools = []
    for index, workload in enumerate(intent["workloads"]):
        vector = {
            "vcpus": workload["compute"]["vcpus"],
            "memory_mib": workload["compute"]["memory_mib"],
            "storage_gib": sum(d["size_gib"] for d in workload["disks"]),
            "addresses": sum(len(n["address_families"]) for n in workload["nics"]),
        }
        pools.append({
            "id": "pool-" + str(index),
            "native_ref": "fixture://physical-host-" + str(index),
            "failure_domain": "rack-" + str(index),
            "zone": "zone-1",
            "zone_allowed": True,
            "architecture": "x86_64",
            "storage_classes": ["standard"],
            "network_classes": ["private"],
            "policy_sha256": digest(policy),
            "ledger_revision": 1,
            "total": vector,
            "used": {k: 0 for k in vector},
            "pending": {k: 0 for k in vector},
        })
    return {
        "definition_sha256": DEFINITION_SHA256,
        "source_sha256": q["verification"]["runtime_sha256"],
        "decision_sha256": q["verification"]["decision_sha256"],
        "scope_sha256": digest(q["scope"]),
        "observed_at": NOW,
        "expires_at": NOW + 120,
        "data": {"pools": pools},
    }
