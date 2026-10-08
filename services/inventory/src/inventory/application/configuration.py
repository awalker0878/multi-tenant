"Inventory owns API facts and immutable, scoped administrator reviews of those facts."

from typing import Any

from inventory.application.discovery import Discovery
from inventory.application.ports import Transaction
from inventory.domain.configuration import (
    AHV_CAPABILITIES,
    CAPABILITIES,
    MANUAL_FIELDS,
    VERSIONS,
    manual_input,
)
from inventory.domain.discovery import Actor, Rejected, canonical, digest, identifier, shape


class PortingConfiguration:
    def __init__(self, discovery: Discovery) -> None:
        self.discovery = discovery

    def authorize(self, actor: Actor) -> None:
        if actor.action != "inventory.admin" or actor.site is None:
            raise Rejected("action_denied", 403)

    def snapshot(
        self, tx: Transaction, actor: Actor, endpoint: str | None
    ) -> dict[str, Any] | None:
        if endpoint is None:
            return None
        d = self.discovery
        e = d.endpoint(tx, actor, endpoint)
        rows = tx.all(
            "SELECT * FROM inventory.configuration_facts WHERE tenant=%s AND endpoint=%s "
            "AND generation=%s ORDER BY query",
            (actor.tenant, endpoint, e["current_generation"]),
        )
        if e["platform"] == "ahv":
            from inventory.application.workload import WorkloadProfiles

            profiles = tx.all(
                "SELECT id FROM inventory.workload_profiles WHERE tenant=%s AND endpoint=%s "
                "AND generation=%s AND profile_type='TargetCapabilityProfile'",
                (actor.tenant, endpoint, e["current_generation"]),
            )
            if len(profiles) != 1:
                return None
            profile = WorkloadProfiles(d).profile(tx, actor, str(profiles[0]["id"]))
            queries = []
            for cap in AHV_CAPABILITIES:
                field = cap["id"].removeprefix("ahv_")
                queries.append(
                    {
                        "query": cap["query"],
                        "status": "observed",
                        "items": [
                            {
                                "id": row["extId"],
                                "name": row.get("name") or row.get("value") or row["extId"],
                                "attributes": [
                                    {"key": k, "value": canonical(v)}
                                    for k, v in row.items()
                                    if k != "extId"
                                ],
                            }
                            for row in profile["facts"][field]
                        ],
                        "collected_at": profile["collected_at"],
                        "expires_at": profile["expires_at"],
                    }
                )
            return {
                "endpoint_id": endpoint,
                "generation_id": profile["generation_id"],
                "current": profile["current"],
                "digest": profile["digest"],
                "queries": queries,
            }
        current = False
        try:
            p = d.policy(e)
            d.collection_authority(p)
            current = bool(rows) and all(row["expires_at"] > d.clock() for row in rows)
        except Rejected:
            pass
        return {
            "endpoint_id": endpoint,
            "generation_id": str(e["current_generation"]) if e["current_generation"] else None,
            "current": current,
            "digest": digest([e["policy_digest"], [row["payload"] for row in rows]]),
            "queries": [
                {
                    **row["payload"],
                    "collected_at": row["collected_at"],
                    "expires_at": row["expires_at"],
                }
                for row in rows
            ],
        }

    def bindings(
        self, source: dict[str, Any] | None, target: dict[str, Any] | None
    ) -> dict[str, Any]:
        return {
            role: {key: snapshot[key] for key in ("endpoint_id", "generation_id", "digest")}
            if snapshot
            else None
            for role, snapshot in (("source", source), ("target", target))
        }

    def state(self, snapshot: dict[str, Any] | None, capability: dict[str, str]) -> str:
        if snapshot is None or not snapshot["current"]:
            return "unknown"
        query = next((q for q in snapshot["queries"] if q["query"] == capability["query"]), None)
        if query is None or query["status"] != "observed":
            return "unknown"
        present = (
            any(item["id"] == capability["match"] for item in query["items"])
            if capability["match"]
            else bool(query["items"])
        )
        return capability["meaning"] if present else "not_observed"

    def read(self, actor: Actor) -> dict[str, Any]:
        self.authorize(actor)
        with self.discovery.database.transaction() as tx:
            return self.view(tx, actor)

    def view(self, tx: Transaction, actor: Actor) -> dict[str, Any]:
        row = tx.one(
            "SELECT * FROM inventory.porting_revisions WHERE tenant=%s AND "
            "site=%s ORDER BY revision DESC LIMIT 1",
            (actor.tenant, actor.site),
        )
        endpoints = tx.all(
            "SELECT id,label,platform FROM inventory.endpoints WHERE "
            "tenant=%s AND site=%s AND NOT revoked ORDER BY id LIMIT 51",
            (actor.tenant, actor.site),
        )
        if len(endpoints) > 50:
            raise Rejected("configuration_endpoint_bound", 409)
        source = self.snapshot(tx, actor, row["payload"]["source_endpoint"]) if row else None
        target = self.snapshot(tx, actor, row["payload"]["target_endpoint"]) if row else None
        configuration = None
        holds = []
        if row:
            confirm = tx.one(
                "SELECT actor,confirmed_at FROM inventory.porting_confirmations "
                "WHERE tenant=%s AND site=%s AND revision=%s",
                (actor.tenant, actor.site, row["revision"]),
            )
            if row["payload"]["bindings"] != self.bindings(source, target):
                holds.append("api_configuration_changed")
            if not source or not target or not source["current"] or not target["current"]:
                holds.append("fresh_source_and_target_configuration_required")
            configuration = {
                "revision": row["revision"],
                "digest": row["digest"],
                "source_endpoint": row["payload"]["source_endpoint"],
                "target_endpoint": row["payload"]["target_endpoint"],
                "manual": row["payload"]["manual"],
                "choices": row["payload"]["choices"],
                "confirmed_by": str(confirm["actor"]) if confirm else None,
                "confirmed_at": confirm["confirmed_at"] if confirm else None,
                "confirmation_current": bool(confirm) and not holds,
            }
        capabilities = [
            {
                **cap,
                "source_state": self.state(source, cap),
                "target_state": self.state(target, cap),
            }
            for cap in CAPABILITIES
        ]
        # Unknown/advertised and administrator overrides are never native support evidence.
        for snapshot in (source, target):
            if snapshot:
                for query in snapshot["queries"]:
                    query["item_count"] = len(query["items"])
                    query["items"] = query["items"][:5]
        return {
            "versions": VERSIONS,
            "manual_fields": [{"id": key, "label": label} for key, label in MANUAL_FIELDS.items()],
            "endpoints": [
                {"id": str(e["id"]), "label": e["label"], "platform": e["platform"]}
                for e in endpoints
            ],
            "configuration": configuration,
            "source": source,
            "target": target,
            "capabilities": capabilities,
            "ahv_capabilities": [
                {
                    **cap,
                    "source_state": self.state(source, cap),
                    "target_state": self.state(target, cap),
                }
                for cap in AHV_CAPABILITIES
            ],
            "holds": holds,
            "native_write_authorized": False,
        }

    def command(
        self,
        actor: Actor,
        operation: str,
        body: dict[str, Any],
        key: str,
        target: str | None = None,
        expected: int | None = None,
    ) -> dict[str, Any]:
        self.authorize(actor)
        identifier(key)
        if operation not in {"configuration_save", "configuration_confirm"} or target is not None:
            raise Rejected("invalid_operation")
        bound = digest([operation, actor.site, expected, body])
        d = self.discovery
        with d.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7404001)")
            prior = tx.one(
                "SELECT * FROM inventory.commands WHERE tenant=%s AND actor=%s AND command_key=%s",
                (actor.tenant, actor.actor, key),
            )
            if prior:
                if prior["digest"] != bound:
                    raise Rejected("idempotency_conflict", 409)
                return dict(prior["result"])
            row = tx.one(
                "SELECT * FROM inventory.porting_revisions WHERE tenant=%s AND "
                "site=%s ORDER BY revision DESC LIMIT 1",
                (actor.tenant, actor.site),
            )
            if row and expected is None:
                raise Rejected("revision_required", 428)
            if expected != (row["revision"] if row else None):
                raise Rejected("stale_revision", 412)
            if operation == "configuration_save":
                platform = "openstack"
                if body.get("target_endpoint") is not None:
                    platform = d.endpoint(tx, actor, identifier(body["target_endpoint"]))[
                        "platform"
                    ]
                manual_input(body, platform)
                for role in ("source", "target"):
                    endpoint = body[role + "_endpoint"]
                    if endpoint is not None:
                        e = d.endpoint(tx, actor, identifier(endpoint))
                        if role == "target" and e["platform"] not in {"openstack", "ahv"}:
                            raise Rejected("supported_target_required")
                source = self.snapshot(tx, actor, body["source_endpoint"])
                destination = self.snapshot(tx, actor, body["target_endpoint"])
                payload = {**body, "bindings": self.bindings(source, destination)}
                revision = row["revision"] + 1 if row else 1
                content_digest = digest(payload)
                tx.execute(
                    "INSERT INTO inventory.porting_revisions VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s)",
                    (
                        actor.tenant,
                        actor.site,
                        revision,
                        canonical(payload),
                        content_digest,
                        actor.actor,
                        d.clock(),
                    ),
                )
            else:
                shape(body, {"digest"})
                if row is None or body["digest"] != row["digest"]:
                    raise Rejected("stale_configuration", 412)
                view = self.view(tx, actor)
                if view["holds"]:
                    raise Rejected("configuration_refresh_required", 409)
                # Acknowledge disclosed gaps; native admission remains held.
                revision, content_digest = row["revision"], row["digest"]
                tx.execute(
                    "INSERT INTO inventory.porting_confirmations VALUES "
                    "(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (actor.tenant, actor.site, revision, content_digest, actor.actor, d.clock()),
                )
            result = {
                "revision": revision,
                "digest": content_digest,
                "native_write_authorized": False,
            }
            d.record(tx, actor.tenant, actor.actor, operation, actor.site or "", result)
            tx.execute(
                "INSERT INTO inventory.commands VALUES (%s,%s,%s,%s,%s::jsonb)",
                (actor.tenant, actor.actor, key, bound, canonical(result)),
            )
            return result
