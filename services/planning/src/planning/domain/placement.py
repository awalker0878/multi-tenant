"""Bounded concrete vector placement, explicit policy and physical failure domains."""

from typing import Any

from planning.domain.model import digest


class PlacementUnknown(ValueError):
    pass


def amount(value: Any) -> int:
    if type(value) is not int or value < 0 or value > 2**53 - 1:
        raise PlacementUnknown("placement_resource_unit_invalid")
    return value


def workload_vector(workload: dict[str, Any]) -> dict[str, int]:
    result = {
        "vcpus": amount(workload["compute"]["vcpus"]),
        "memory_mib": amount(workload["compute"]["memory_mib"]),
        "storage_gib": sum(amount(d["size_gib"]) for d in workload["disks"]),
        "addresses": sum(len(n["address_families"]) for n in workload["nics"]),
    }
    for disk in workload["disks"]:
        key = "storage_gib:" + disk["storage_class"]
        result[key] = result.get(key, 0) + amount(disk["size_gib"])
    for nic in workload["nics"]:
        for family in nic["address_families"]:
            key = "addresses:" + nic["network_class"] + ":" + family
            result[key] = result.get(key, 0) + 1
    return result


def fit(
    intent: dict[str, Any], pools: list[dict[str, Any]], policy: dict[str, Any], now: int
) -> dict[str, Any]:
    if not 1 <= len(pools) <= 128 or len({p["id"] for p in pools}) != len(pools):
        raise PlacementUnknown("placement_pool_bound_or_ambiguous")
    workloads = sorted(
        intent["workloads"],
        key=lambda w: (-workload_vector(w)["memory_mib"], w["id"]),
    )
    free: dict[str, dict[str, int]] = {}
    for pool in pools:
        if (
            pool["policy_sha256"] != digest(policy)
            or not pool["native_ref"]
            or not pool["failure_domain"]
            or not pool["zone"]
            or type(pool["ledger_revision"]) is not int
            or pool["ledger_revision"] < 1
        ):
            raise PlacementUnknown("placement_pool_identity_or_policy_missing")
        limits = {k: amount(v) for k, v in pool["total"].items()}
        overcommit = pool.get("overcommit")
        if overcommit is not None:
            if (
                set(overcommit) != {"numerator", "denominator", "approved_by", "expires_at"}
                or not overcommit["approved_by"]
                or amount(overcommit["expires_at"]) <= now
                or amount(overcommit["denominator"]) < 1
                or amount(overcommit["numerator"]) < overcommit["denominator"]
            ):
                raise PlacementUnknown("placement_overcommit_policy_invalid")
            limits["vcpus"] = (
                limits["vcpus"] * overcommit["numerator"] // overcommit["denominator"]
            )
        free[pool["id"]] = {
            k: limits[k] - amount(pool["used"][k]) - amount(pool["pending"][k])
            for k in limits
        }
        if any(v < 0 for v in free[pool["id"]].values()):
            return {"status": "blocked", "reason": "placement_pool_overallocated", "allocations": []}
    selected: list[dict[str, Any]] = []
    visited = 0

    def search(index: int) -> bool:
        nonlocal visited
        visited += 1
        if visited > 20000:
            raise PlacementUnknown("placement_search_bound")
        if index == len(workloads):
            return True
        workload = workloads[index]
        vector = workload_vector(workload)
        failure = workload["failure_domain"]
        for pool in sorted(pools, key=lambda p: p["id"]):
            if (
                workload["compute"]["architecture"] != pool["architecture"]
                or any(d["storage_class"] not in pool["storage_classes"] for d in workload["disks"])
                or any(n["network_class"] not in pool["network_classes"] for n in workload["nics"])
                or pool["zone"] not in policy["allowed_zones"]
                or any(free[pool["id"]].get(k, -1) < v for k, v in vector.items())
            ):
                continue
            siblings = [r for r in selected if r["failure_group"] == failure["group"]]
            if failure["strength"] == "required" and any(
                (failure["mode"] == "anti_affinity" and r["failure_domain"] == pool["failure_domain"])
                or (failure["mode"] == "affinity" and r["failure_domain"] != pool["failure_domain"])
                for r in siblings
            ):
                continue
            allocation = {
                "workload_id": workload["id"],
                "pool_id": pool["id"],
                "native_ref": pool["native_ref"],
                "failure_domain": pool["failure_domain"],
                "failure_group": failure["group"],
                "vector": vector,
                "ledger_revision": pool["ledger_revision"],
            }
            selected.append(allocation)
            for kind, value in vector.items():
                free[pool["id"]][kind] -= value
            if search(index + 1):
                return True
            selected.pop()
            for kind, value in vector.items():
                free[pool["id"]][kind] += value
        return False

    placed = search(0)
    return {
        "status": "eligible" if placed else "blocked",
        "reason": "concrete_placement_unreserved" if placed else "placement_fragmented_or_constrained",
        "allocations": selected if placed else [],
    }
