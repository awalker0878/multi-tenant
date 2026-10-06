"Bounded tenant/site projections; historical observations retain their own timestamps."

from typing import Any

from inventory.application.discovery import Discovery, uuid_value
from inventory.domain.discovery import Actor, Rejected, identifier, profile


class InventoryViews:
    def __init__(self, discovery: Discovery) -> None:
        self.discovery = discovery

    def read(
        self, actor: Actor, operation: str, target: str | None = None, cursor: str | None = None
    ) -> dict[str, Any]:
        if actor.action not in {"inventory.read", "inventory.admin"}:
            raise Rejected("action_denied", 403)
        d = self.discovery
        after = uuid_value(cursor) if cursor else "00000000-0000-0000-0000-000000000000"
        now = d.clock()
        with d.database.transaction() as tx:
            if operation == "sites":
                rows = tx.all(
                    (
                        "SELECT DISTINCT site FROM inventory.endpoints WHERE "
                        "tenant=%s AND site>%s ORDER BY site LIMIT 51"
                    ),
                    (actor.tenant, after),
                )
                return {
                    "items": [{"site_id": str(r["site"])} for r in rows[:50]],
                    "next_cursor": str(rows[49]["site"]) if len(rows) > 50 else None,
                }
            if operation == "policies":
                if actor.action != "inventory.admin":
                    raise Rejected("action_denied", 403)
                return {
                    "items": [
                        p.public()
                        for p in d.policies.load().values()
                        if (p.tenant, p.site, p.owner) == (actor.tenant, actor.site, actor.actor)
                    ][:50],
                    "next_cursor": None,
                }
            if operation == "endpoints":
                rows = tx.all(
                    (
                        "SELECT e.*,j.status AS generation_status,j.created_at "
                        "AS generation_started,latest.status AS "
                        "latest_status,latest.reason AS latest_reason FROM "
                        "inventory.endpoints e LEFT JOIN inventory.jobs j ON "
                        "j.id=e.current_generation LEFT JOIN LATERAL (SELECT "
                        "status,reason FROM inventory.jobs WHERE endpoint=e.id "
                        "ORDER BY created_at DESC,id DESC LIMIT 1) latest ON "
                        "true WHERE e.tenant=%s AND e.site=%s AND e.id>%s ORDER "
                        "BY e.id LIMIT 51"
                    ),
                    (actor.tenant, actor.site, after),
                )
                items = []
                for row in rows[:50]:
                    try:
                        policy = d.policy(row)
                        expiry = (row["generation_started"] or 0) + policy.freshness_seconds
                        reason = (
                            "never_collected"
                            if not row["current_generation"]
                            else "expired"
                            if expiry <= now
                            else row["latest_reason"]
                            or ("collecting" if row["latest_status"] != "complete" else None)
                        )
                        facts = profile(policy.platform, policy.installed)
                        coverage = policy.coverage_reference
                    except Rejected:
                        expiry, reason, coverage = None, "enrollment_unavailable", None
                        facts = profile(row["platform"], {})
                    items.append(
                        {
                            "endpoint_id": str(row["id"]),
                            "site_id": str(row["site"]),
                            "label": row["label"],
                            "platform": row["platform"],
                            "native_scope": row["native_scope"],
                            "revision": row["revision"],
                            "generation_id": str(row["current_generation"])
                            if row["current_generation"]
                            else None,
                            "expires_at": expiry,
                            "state": "read_only_ready" if reason is None else "held",
                            "reason": reason,
                            "coverage_reference": coverage,
                            "profile": facts,
                            "native_write_authorized": False,
                            "observed_capacity_reserved": False,
                        }
                    )
                return {
                    "items": items,
                    "next_cursor": str(rows[49]["id"]) if len(rows) > 50 else None,
                }
            if operation == "discoveries":
                d.endpoint(tx, actor, target or "")
                rows = tx.all(
                    (
                        "SELECT id,status,reason,created_at,updated_at,page_coun"
                        "t,failures FROM inventory.jobs WHERE tenant=%s AND "
                        "endpoint=%s AND id>%s ORDER BY id LIMIT 51"
                    ),
                    (actor.tenant, target, after),
                )
                return {
                    "items": [{**r, "id": str(r["id"])} for r in rows[:50]],
                    "next_cursor": str(rows[49]["id"]) if len(rows) > 50 else None,
                }
            if operation == "resources":
                job = tx.one(
                    (
                        "SELECT j.*,e.site FROM inventory.jobs j JOIN "
                        "inventory.endpoints e ON e.id=j.endpoint WHERE j.id=%s "
                        "AND j.tenant=%s AND e.site=%s"
                    ),
                    (identifier(target), actor.tenant, actor.site),
                )
                if job is None:
                    raise Rejected("not_found", 404)
                e = d.endpoint(tx, actor, str(job["endpoint"]))
                enrolled = True
                try:
                    d.policy(e)
                except Rejected:
                    enrolled = False
                rows = tx.all(
                    (
                        "SELECT r.id,r.identity_hold,r.tombstone,r.absent_count,"
                        "o.payload,o.collected_at,o.expires_at,(SELECT "
                        "count(DISTINCT application) FROM inventory.matches m "
                        "WHERE m.resource=r.id AND m.tenant=%s) AS candidates "
                        "FROM inventory.observations o JOIN inventory.resources "
                        "r ON r.id=o.resource WHERE o.tenant=%s AND "
                        "o.generation=%s AND r.id>%s ORDER BY r.id LIMIT 51"
                    ),
                    (actor.tenant, actor.tenant, target, after),
                )
                items = []
                for r in rows[:50]:
                    holds = []
                    if not enrolled:
                        holds.append("enrollment_unavailable")
                    if job["status"] != "complete":
                        holds.append("incomplete_generation")
                    if str(e["current_generation"]) != target:
                        holds.append("historical_generation")
                    if r["expires_at"] <= now:
                        holds.append("expired")
                    if r["identity_hold"]:
                        holds.append("identity_ambiguous")
                    if r["tombstone"] or r["absent_count"]:
                        holds.append("absent_in_newer_generation")
                    if r["candidates"] > 1:
                        holds.append("ownership_collision")
                    items.append(
                        {
                            "resource_id": str(r["id"]),
                            "observation": r["payload"],
                            "collected_at": r["collected_at"],
                            "expires_at": r["expires_at"],
                            "holds": holds,
                            "proposed_matches": r["candidates"],
                            "ownership": "observation_only",
                            "reserved": False,
                        }
                    )
                return {
                    "items": items,
                    "next_cursor": str(rows[49]["id"]) if len(rows) > 50 else None,
                    "generation_id": target,
                    "completion": job["status"],
                    "reason": job["reason"],
                    "endpoint_id": str(e["id"]),
                    "policy_digest": job["policy_digest"],
                    "consistency": "bounded_observation_window",
                }
            if operation == "health":
                # Tenant-scoped metrics omit shared endpoint totals and other tenants.
                rows = tx.all(
                    (
                        "SELECT j.status,count(*) AS count,max(j.updated_at) AS "
                        "last_activity FROM inventory.jobs j JOIN "
                        "inventory.endpoints e ON e.id=j.endpoint WHERE "
                        "j.tenant=%s AND e.site=%s GROUP BY j.status ORDER BY "
                        "j.status"
                    ),
                    (actor.tenant, actor.site),
                )
                return {"items": rows, "observed_at": now}
        raise Rejected("not_found", 404)
