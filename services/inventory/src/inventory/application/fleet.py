"""Scoped API inventory and durable groups feeding independent per-VM preparations."""

from typing import Any
from uuid import UUID, uuid5

from inventory.application.discovery import Discovery, uid, uuid_value
from inventory.application.ports import Transaction
from inventory.application.workload import WorkloadProfiles
from inventory.domain.discovery import Actor, Rejected, canonical, digest, identifier, shape, text


class MigrationFleet:
    def __init__(self, discovery: Discovery) -> None:
        self.d = discovery
        self.profiles = WorkloadProfiles(discovery)

    def candidate(
        self,
        tx: Transaction,
        actor: Actor,
        resource: str,
        authority_cache: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        r = tx.one(
            "SELECT "
            "r.*,e.label,e.native_scope,e.current_generation,o.payload,o.collected_at,o.expires_at "
            "FROM inventory.resources r JOIN inventory.endpoints e ON e.id=r.endpoint "
            "JOIN inventory.observations o ON o.resource=r.id AND o.generation=r.last_generation "
            "WHERE r.id=%s AND r.tenant=%s AND e.site=%s AND e.platform='vmware' AND "
            "r.kind='server'",
            (uuid_value(resource), actor.tenant, actor.site),
        )
        if r is None:
            raise Rejected("not_found", 404)
        endpoint = self.d.endpoint(tx, actor, str(r["endpoint"]))
        holds = []
        try:
            policy = self.d.policy(endpoint)
            if authority_cache is None or policy.policy_digest not in authority_cache:
                try:
                    self.d.collection_authority(policy)
                except Rejected:
                    if authority_cache is not None:
                        authority_cache[policy.policy_digest] = False
                    raise
                if authority_cache is not None:
                    authority_cache[policy.policy_digest] = True
            if authority_cache is not None and not authority_cache[policy.policy_digest]:
                raise Rejected("collection_authority_unavailable", 503)
        except Rejected:
            holds.append("source_enrollment_unavailable")
        if r["expires_at"] <= self.d.clock():
            holds.append("source_inventory_expired")
        if r["tombstone"] or r["absent_count"] or r["last_generation"] != r["current_generation"]:
            holds.append("source_absent_or_generation_changed")
        row = tx.one(
            "SELECT id FROM inventory.workload_profiles WHERE tenant=%s AND endpoint=%s "
            "AND generation=%s AND native_id=%s AND profile_type='SourceWorkloadProfile'",
            (actor.tenant, r["endpoint"], r["last_generation"], r["native_id"]),
        )
        profile = self.profiles.profile(tx, actor, str(row["id"]), authority_cache) if row else None
        facts = profile["facts"] if profile else {}
        if not profile:
            holds.append("source_profile_required")
        elif not profile["current"]:
            holds.append("source_profile_stale")
        holds.extend("source_" + h for h in facts.get("holds", []))
        identity = self.profiles.binding(profile)["native_identity_sha256"] if profile else None
        if profile and (not facts.get("instance_uuid") or not facts.get("vcenter_uuid")):
            holds.append("source_identity_required")
        observation = r["payload"]
        return {
            "resource_id": resource,
            "endpoint_id": str(r["endpoint"]),
            "endpoint_label": r["label"],
            "native_scope": r["native_scope"],
            "native_id": r["native_id"],
            "name": observation["name"],
            "generation_id": str(r["last_generation"]),
            "profile_id": profile["id"] if profile else None,
            "source_identity_sha256": identity,
            "power_state": facts.get("power_state") or observation["facts"].get("power"),
            "cpu": facts.get("cpu") or observation["facts"].get("cpu"),
            "memory_mb": facts.get("memory_mb") or observation["facts"].get("memory_mib"),
            "guest_id": facts.get("guest_id"),
            "disk_count": len(facts.get("disks", [])) if profile else None,
            "disk_bytes": sum(d.get("capacity_bytes") or 0 for d in facts.get("disks", []))
            if profile
            else None,
            "collected_at": r["collected_at"],
            "expires_at": min(r["expires_at"], profile["expires_at"])
            if profile
            else r["expires_at"],
            "holds": holds,
            "readiness": "held" if holds else "review_required",
        }

    def read(self, actor: Actor, cursor: str | None = None) -> dict[str, Any]:
        self.profiles.authorize(actor)
        after = uuid_value(cursor) if cursor else "00000000-0000-0000-0000-000000000000"
        authority_cache: dict[str, bool] = {}
        with self.d.database.transaction() as tx:
            rows = tx.all(
                "SELECT r.id FROM inventory.resources r JOIN inventory.endpoints e ON "
                "e.id=r.endpoint "
                "WHERE r.tenant=%s AND e.site=%s AND e.platform='vmware' AND r.kind='server' "
                "AND r.id>%s ORDER BY r.id LIMIT 51",
                (actor.tenant, actor.site, after),
            )
            targets = tx.all(
                "SELECT p.id FROM inventory.workload_profiles p JOIN "
                "inventory.endpoints e ON e.id=p.endpoint "
                "WHERE p.tenant=%s AND e.site=%s AND p.generation=e.current_generation "
                "AND p.profile_type='TargetCapabilityProfile' AND NOT e.revoked ORDER "
                "BY p.id LIMIT 51",
                (actor.tenant, actor.site),
            )
            groups = tx.all(
                "SELECT DISTINCT ON (id) * FROM inventory.migration_groups WHERE "
                "tenant=%s AND site=%s "
                "ORDER BY id,revision DESC LIMIT 101",
                (actor.tenant, actor.site),
            )
            if len(targets) > 50 or len(groups) > 100:
                raise Rejected("migration_workspace_bound", 409)
            target_items = []
            for row in targets:
                p = self.profiles.profile(tx, actor, str(row["id"]), authority_cache)
                target_items.append(
                    {
                        "id": p["id"],
                        "native_id": p["native_id"],
                        "current": p["current"],
                        "expires_at": p["expires_at"],
                        "holds": p["facts"]["holds"],
                        "disk_formats": p["facts"]["disk_formats"],
                    }
                )
            return {
                "items": [
                    self.candidate(tx, actor, str(r["id"]), authority_cache) for r in rows[:50]
                ],
                "next_cursor": str(rows[49]["id"]) if len(rows) > 50 else None,
                "targets": target_items,
                "groups": [self.group_row(r) for r in groups],
                "native_write_authorized": False,
            }

    @staticmethod
    def group_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "revision": row["revision"],
            "digest": row["digest"],
            "input": row["payload"],
        }

    def group(self, tx: Transaction, actor: Actor, key: str) -> dict[str, Any]:
        row = tx.one(
            "SELECT * FROM inventory.migration_groups WHERE tenant=%s AND site=%s AND id=%s "
            "ORDER BY revision DESC LIMIT 1",
            (actor.tenant, actor.site, identifier(key)),
        )
        if row is None:
            raise Rejected("not_found", 404)
        return self.group_row(row)

    def command(
        self,
        actor: Actor,
        operation: str,
        body: dict[str, Any],
        key: str,
        target: str | None = None,
        expected: int | None = None,
    ) -> dict[str, Any]:
        self.profiles.authorize(actor)
        identifier(key)
        if operation != "migration_group_save":
            raise Rejected("invalid_operation")
        shape(
            body,
            {
                "name",
                "application_id",
                "environment_id",
                "target_profile_id",
                "format",
                "resource_ids",
            },
        )
        text(body["name"], 120)
        for field in ("application_id", "environment_id", "target_profile_id"):
            identifier(body[field])
        members = body["resource_ids"]
        if not isinstance(members, list) or not 1 <= len(members) <= 50:
            raise Rejected("migration_group_bound")
        members = [uuid_value(m) for m in members]
        if len(set(members)) != len(members):
            raise Rejected("duplicate_migration_member")
        if body["format"] not in {"raw", "qcow2"}:
            raise Rejected("migration_format_invalid")
        bound = digest([operation, actor.site, target, expected, body])
        with self.d.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7404001)")
            previous = tx.one(
                "SELECT * FROM inventory.commands WHERE tenant=%s AND actor=%s AND command_key=%s",
                (actor.tenant, actor.actor, key),
            )
            if previous:
                if previous["digest"] != bound:
                    raise Rejected("idempotency_conflict", 409)
                return dict(previous["result"])
            current = self.group(tx, actor, target) if target else None
            if current and expected is None:
                raise Rejected("revision_required", 428)
            if expected != (current["revision"] if current else None):
                raise Rejected("stale_revision", 412)
            if not current:
                count = tx.one(
                    "SELECT count(DISTINCT id) AS n FROM inventory.migration_groups "
                    "WHERE tenant=%s AND site=%s",
                    (actor.tenant, actor.site),
                )
                if count and count["n"] >= 100:
                    raise Rejected("migration_workspace_bound", 409)
            destination = self.profiles.profile(tx, actor, body["target_profile_id"])
            if (
                destination["profile_type"] != "TargetCapabilityProfile"
                or destination["facts"]["platform"] != "openstack"
            ):
                raise Rejected("openstack_target_required")
            if (
                not destination["current"]
                or body["format"] not in destination["facts"]["disk_formats"]
            ):
                raise Rejected("target_profile_stale_or_format_unavailable", 409)
            authority_cache: dict[str, bool] = {}
            selected = [
                self.candidate(tx, actor, resource, authority_cache) for resource in sorted(members)
            ]
            payload = {k: v for k, v in body.items() if k != "resource_ids"}
            payload["members"] = [
                {
                    "resource_id": m["resource_id"],
                    "source_identity_sha256": m["source_identity_sha256"],
                }
                for m in selected
            ]
            group_id, revision = (current["id"], current["revision"] + 1) if current else (uid(), 1)
            content_digest = digest(payload)
            tx.execute(
                "INSERT INTO inventory.migration_groups VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s,%s)",
                (
                    group_id,
                    actor.tenant,
                    actor.site,
                    revision,
                    canonical(payload),
                    content_digest,
                    actor.actor,
                    self.d.clock(),
                ),
            )
            result = {
                "id": group_id,
                "revision": revision,
                "digest": content_digest,
                "native_write_authorized": False,
            }
            self.d.record(tx, actor.tenant, actor.actor, operation, group_id, result)
            tx.execute(
                "INSERT INTO inventory.commands VALUES(%s,%s,%s,%s,%s::jsonb)",
                (actor.tenant, actor.actor, key, bound, canonical(result)),
            )
            return result

    def detail(self, actor: Actor, group_id: str) -> dict[str, Any]:
        self.profiles.authorize(actor)
        authority_cache: dict[str, bool] = {}
        with self.d.database.transaction() as tx:
            group = self.group(tx, actor, group_id)
            target = self.profiles.profile(
                tx, actor, group["input"]["target_profile_id"], authority_cache
            )
            results = []
            for member in group["input"]["members"]:
                c = self.candidate(tx, actor, member["resource_id"], authority_cache)
                holds = list(c["holds"])
                if not target["current"]:
                    holds.append("target_profile_stale")
                holds.extend("target_" + h for h in target["facts"]["holds"])
                if group["input"]["format"] not in target["facts"]["disk_formats"]:
                    holds.append("target_format_unavailable")
                if (
                    not member["source_identity_sha256"]
                    or member["source_identity_sha256"] != c["source_identity_sha256"]
                ):
                    holds.append("group_source_identity_requires_review")
                review = (
                    self.profiles.review(tx, actor, c["profile_id"], authority_cache)
                    if c["profile_id"]
                    else None
                )
                if not review or not review["confirmation_current"]:
                    holds.append("confirmed_vm_review_required")
                elif (
                    review["source"]["id"] != c["profile_id"]
                    or review["target"]["id"] != target["id"]
                ):
                    holds.append("review_profile_pair_changed")
                request = None
                if not holds and review:
                    request = {
                        "site_id": actor.site,
                        "review": {"revision": review["revision"], "digest": review["digest"]},
                        "disks": [
                            {
                                "source_disk_sha256": disk["native_sha256"],
                                "target_key": str(
                                    uuid5(
                                        UUID(group["id"]),
                                        f"{group['revision']}:{c['resource_id']}:{disk['native_sha256']}",
                                    )
                                ),
                                "format": group["input"]["format"],
                            }
                            for disk in review["source"]["facts"]["disks"]
                        ],
                    }
                results.append({"candidate": c, "holds": holds, "preparation": request})
            return {"group": group, "members": results, "native_write_authorized": False}
