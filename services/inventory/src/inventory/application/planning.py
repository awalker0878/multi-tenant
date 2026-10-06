"""Inventory's owner read for planning, without ownership or capacity inference."""

from typing import Any

from inventory.application.discovery import Discovery
from inventory.domain.discovery import DIMENSIONS, Rejected, identifier


def planning_input(
    d: Discovery, tenant: str, site: str, endpoint: str, generation: str
) -> dict[str, Any]:
    with d.database.transaction() as tx:
        row = tx.one(
            "SELECT * FROM inventory.endpoints WHERE tenant=%s AND site=%s AND id=%s",
            (identifier(tenant), identifier(site), identifier(endpoint)),
        )
        job = tx.one(
            "SELECT * FROM inventory.jobs WHERE tenant=%s AND endpoint=%s AND id=%s",
            (tenant, endpoint, identifier(generation)),
        )
        if row is None or job is None:
            raise Rejected("not_found", 404)
        holds = []
        try:
            policy = d.policy(row)
            d.collection_authority(policy)
            installed = policy.installed
        except Rejected:
            holds.append("enrollment_unavailable")
            installed = {}
        stats = tx.one(
            "SELECT min(o.expires_at) AS expires,count(*) AS n, bool"
            "_or(r.identity_hold OR r.tombstone OR r.absent_count>0)"
            " AS held FROM inventory.observations o JOIN inventory.r"
            "esources r ON r.id=o.resource WHERE o.tenant=%s AND o.g"
            "eneration=%s",
            (tenant, generation),
        )
        if not stats or not stats["n"]:
            holds.append("observations_missing")
        elif stats["held"]:
            holds.append("identity_or_absence_hold")
        collision = tx.one(
            "SELECT r.id FROM inventory.resources r JOIN inventory.m"
            "atches m ON m.resource=r.id WHERE r.tenant=%s AND r.end"
            "point=%s GROUP BY r.id HAVING count(DISTINCT m.applicat"
            "ion)>1 LIMIT 1",
            (tenant, endpoint),
        )
        if collision:
            holds.append("ownership_collision")
        return {
            "tenant_id": tenant,
            "site_id": site,
            "endpoint_id": endpoint,
            "generation_id": generation,
            "platform": row["platform"],
            "native_scope": row["native_scope"],
            "current": str(row["current_generation"]) == generation,
            "completion": job["status"],
            "expires_at": int(stats["expires"] or 0) if stats else 0,
            "holds": holds,
            "installed_provenance": "declaration",
            "installed_tuple": installed,
            "dimensions": {name: "unassessed" for name in DIMENSIONS},
            "capabilities": {},
            "capacity": {},
            "domain_bindings": {},
            "workload_bindings": {},
        }
