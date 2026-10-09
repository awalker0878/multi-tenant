"""Inventory-owned profile history, exact review bindings and current Planning reads."""

from typing import Any

from inventory.application.discovery import Discovery
from inventory.application.ports import Transaction
from inventory.domain.discovery import Actor, Rejected, canonical, digest, identifier, shape
from inventory.domain.migration import destination_input
from inventory.domain.destination_security import source_rule_choices, source_security_ids
from inventory.domain.source_profile import source_identity, source_observation
from inventory.domain.workload import METHODS, OWNER_FIELDS, review_input


class WorkloadProfiles:
    def __init__(self, discovery: Discovery, collection_read=None) -> None:
        self.d = discovery
        self.collection_read = collection_read

    def authorize(self, actor: Actor) -> None:
        if actor.action != "inventory.admin" or actor.site is None:
            raise Rejected("action_denied", 403)

    def profile(
        self,
        tx: Transaction,
        actor: Actor,
        key: str,
        authority_cache: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        row = tx.one(
            "SELECT p.* FROM inventory.workload_profiles p JOIN inventory.endpoints e "
            "ON e.id=p.endpoint WHERE p.tenant=%s AND e.site=%s AND p.id=%s",
            (actor.tenant, actor.site, identifier(key)),
        )
        if row is None:
            raise Rejected("not_found", 404)
        e = self.d.endpoint(tx, actor, str(row["endpoint"]))
        current = False
        try:
            policy = self.d.policy(e)
            cache_key = policy.policy_digest
            if authority_cache is None or cache_key not in authority_cache:
                try:
                    self.d.collection_authority(policy)
                except Rejected:
                    if authority_cache is not None:
                        authority_cache[cache_key] = False
                    raise
                if authority_cache is not None:
                    authority_cache[cache_key] = True
            if authority_cache is not None and not authority_cache[cache_key]:
                raise Rejected("collection_authority_unavailable", 503)
            current = (
                row["policy_digest"] == policy.policy_digest
                and e["current_generation"] == row["generation"]
                and row["expires_at"] > self.d.clock()
            )
        except Rejected:
            pass
        return {
            "id": str(row["id"]),
            "endpoint_id": str(row["endpoint"]),
            "generation_id": str(row["generation"]),
            "native_id": row["native_id"],
            "profile_type": row["profile_type"],
            "digest": row["digest"],
            "current": current,
            "expires_at": row["expires_at"],
            "collected_at": row["collected_at"],
            "facts": row["payload"],
        }

    def binding(self, profile: dict[str, Any]) -> dict[str, Any]:
        p = profile["facts"]
        source = p["profile_type"] == "SourceWorkloadProfile"
        identity = [
            p.get(k)
            for k in (("vcenter_uuid", "vm_id", "instance_uuid") if source else ("project_id",))
        ]
        installed = [
            p.get(k)
            for k in (
                ("vcenter_version", "native_api_version", "api_version", "guest_id", "firmware")
                if source
                else ("compute_version", "volume_version")
            )
        ]
        if source:
            identity, installed = source_identity(p)
        elif p["platform"] == "ahv":
            identity = [p[k] for k in ("project_id", "prism_central_id", "cluster_id")]
            installed = [p["api_versions"], p["installed"]]
        elif p["platform"] == "vmware":
            identity = [p[k] for k in ("project_id", "vcenter_uuid")]
            installed = [p["api_version"], p["installed"]]
        return {
            "profile_sha256": profile["digest"],
            "native_identity_sha256": digest([profile["endpoint_id"], identity]),
            "tuple_sha256": digest(installed),
            "observed_at": int(profile["collected_at"]),
            "expires_at": int(profile["expires_at"]),
        }

    def review(
        self,
        tx: Transaction,
        actor: Actor,
        source_id: str | None = None,
        authority_cache: dict[str, bool] | None = None,
    ) -> dict[str, Any] | None:
        if source_id is None:
            row = tx.one(
                "SELECT * FROM inventory.migration_reviews WHERE tenant=%s AND site=%s "
                "ORDER BY revision DESC LIMIT 1",
                (actor.tenant, actor.site),
            )
        else:
            source = self.profile(tx, actor, source_id, authority_cache)
            row = tx.one(
                "SELECT r.* FROM inventory.migration_reviews r JOIN inventory.workload_profiles p "
                "ON p.id=(r.payload->>'source_profile_id')::uuid "
                "WHERE r.tenant=%s AND r.site=%s AND p.endpoint=%s AND p.native_id=%s "
                "ORDER BY r.revision DESC LIMIT 1",
                (actor.tenant, actor.site, source["endpoint_id"], source["native_id"]),
            )
        if row is None:
            return None
        payload = row["payload"]
        source = self.profile(tx, actor, payload["source_profile_id"], authority_cache)
        target = self.profile(tx, actor, payload["target_profile_id"], authority_cache)
        holds = []
        if not source["current"] or not target["current"]:
            holds.append("current_source_and_target_profiles_required")
        holds.extend("source_" + h for h in source["facts"]["holds"])
        holds.extend("target_" + h for h in target["facts"]["holds"])
        required_security = source_security_ids(source["facts"])
        if required_security is None:
            holds.append("source_security_policy_observation_required")
        elif required_security and source_rule_choices(source["facts"]) is None:
            holds.append("source_security_rule_observation_required")
        elif required_security and target["facts"]["platform"] == "vmware":
            holds.append("destination_security_policy_catalog_required")
        elif required_security and target["facts"]["platform"] == "ahv":
            # Observed enforced Prism policy membership does not prove the
            # required traffic allows/denies. A separate native E3/E4 check
            # is needed before confirmation and execution.
            holds.append("destination_security_flow_equivalence_unproven")
        confirmed = tx.one(
            "SELECT actor,confirmed_at FROM inventory.migration_confirmations "
            "WHERE tenant=%s AND site=%s AND revision=%s",
            (actor.tenant, actor.site, row["revision"]),
        )
        return {
            "revision": row["revision"],
            "digest": row["digest"],
            "input": payload,
            "source": source,
            "target": target,
            "holds": holds,
            "confirmed_by": str(confirmed["actor"]) if confirmed else None,
            "confirmed_at": confirmed["confirmed_at"] if confirmed else None,
            "confirmation_current": bool(confirmed) and not holds,
        }

    def read(self, actor: Actor, source_id: str | None = None) -> dict[str, Any]:
        self.authorize(actor)
        with self.d.database.transaction() as tx:
            selected = self.profile(tx, actor, source_id) if source_id else None
            if selected and selected["profile_type"] != "SourceWorkloadProfile":
                raise Rejected("invalid_profile_pair")
            rows = tx.all(
                "SELECT p.id FROM inventory.workload_profiles p JOIN inventory.endpoints e "
                "ON e.id=p.endpoint AND e.current_generation=p.generation "
                "WHERE p.tenant=%s AND e.site=%s AND NOT e.revoked "
                "AND (%s::uuid IS NULL OR p.id=%s::uuid OR "
                "p.profile_type='TargetCapabilityProfile') "
                "ORDER BY p.id LIMIT 51",
                (actor.tenant, actor.site, source_id, source_id),
            )
            if len(rows) > 50:
                raise Rejected("profile_workspace_bound", 409)
            result = {
                "profiles": [self.profile(tx, actor, str(p["id"])) for p in rows],
                "review": self.review(tx, actor, source_id),
                "methods": list(METHODS),
                "owner_fields": list(OWNER_FIELDS),
                "native_write_authorized": False,
            }
            if len(canonical(result).encode()) > 1500000:
                raise Rejected("profile_workspace_bound", 409)
            return result

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
        if operation not in {"migration_save", "migration_confirm"}:
            raise Rejected("invalid_operation")
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
            if target is not None:
                selected = self.profile(tx, actor, target)
                if selected["profile_type"] != "SourceWorkloadProfile":
                    raise Rejected("invalid_profile_pair")
                if operation == "migration_save" and body.get("source_profile_id") != target:
                    raise Rejected("source_review_scope_mismatch", 403)
            current = self.review(tx, actor, target)
            if current and expected is None:
                raise Rejected("revision_required", 428)
            if expected != (current["revision"] if current else None):
                raise Rejected("stale_revision", 412)
            if operation == "migration_save":
                source = self.profile(tx, actor, body.get("source_profile_id", ""))
                destination = self.profile(tx, actor, body.get("target_profile_id", ""))
                if (
                    source["profile_type"] != "SourceWorkloadProfile"
                    or destination["profile_type"] != "TargetCapabilityProfile"
                ):
                    raise Rejected("invalid_profile_pair")
                review_input(body, source["facts"])
                destination_input(body, source["facts"], destination["facts"])
                latest = tx.one(
                    "SELECT COALESCE(MAX(revision),0) AS revision FROM inventory.migration_reviews "
                    "WHERE tenant=%s AND site=%s",
                    (actor.tenant, actor.site),
                )
                assert latest is not None
                revision = latest["revision"] + 1
                content_digest = digest(body)
                tx.execute(
                    "INSERT INTO inventory.migration_reviews VALUES(%s,%s,%s,%s::jsonb,%s,%s,%s)",
                    (
                        actor.tenant,
                        actor.site,
                        revision,
                        canonical(body),
                        content_digest,
                        actor.actor,
                        self.d.clock(),
                    ),
                )
            else:
                shape(body, {"digest"})
                if current is None or body["digest"] != current["digest"]:
                    raise Rejected("stale_migration_review", 412)
                if current["holds"]:
                    raise Rejected("migration_profiles_held", 409)
                revision, content_digest = current["revision"], current["digest"]
                tx.execute(
                    "INSERT INTO inventory.migration_confirmations VALUES(%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT DO NOTHING",
                    (
                        actor.tenant,
                        actor.site,
                        revision,
                        content_digest,
                        actor.actor,
                        self.d.clock(),
                    ),
                )
            result = {
                "revision": revision,
                "digest": content_digest,
                "native_write_authorized": False,
            }
            self.d.record(tx, actor.tenant, actor.actor, operation, actor.site or "", result)
            tx.execute(
                "INSERT INTO inventory.commands VALUES(%s,%s,%s,%s,%s::jsonb)",
                (actor.tenant, actor.actor, key, bound, canonical(result)),
            )
            return result

    def source_associations(
        self, tx: Transaction, actor: Actor, application: str, environment: str
    ) -> list[dict[str, Any]]:
        """All site-local confirmed, current source links for one application.

        Only the Inventory authority derives identities and native generations.
        Old confirmations superseded by a newer review are not silently reused.
        """
        identifier(application)
        identifier(environment)
        records = tx.all(
            "SELECT r.revision,r.digest,r.payload,c.actor AS confirming_actor "
            "FROM inventory.migration_reviews r "
            "JOIN inventory.migration_confirmations c "
            "ON c.tenant=r.tenant AND c.site=r.site "
            "AND c.revision=r.revision AND c.digest=r.digest "
            "WHERE r.tenant=%s AND r.site=%s "
            "AND r.payload->'catalogue_binding'->>'application_id'=%s "
            "AND r.payload->'catalogue_binding'->>'environment_id'=%s "
            "ORDER BY r.revision DESC LIMIT 101",
            (actor.tenant, actor.site, application, environment),
        )
        if len(records) > 100:
            raise Rejected("source_association_workspace_bound", 423)
        result: list[dict[str, Any]] = []
        authority_cache: dict[str, bool] = {}
        for record in records:
            body = record["payload"]
            link = body.get("catalogue_binding")
            if (not isinstance(link, dict)
                    or link.get("application_id") != application
                    or link.get("environment_id") != environment):
                continue
            source = self.profile(tx, actor, body["source_profile_id"], authority_cache)
            selected = self.review(tx, actor, body["source_profile_id"], authority_cache)
            current = bool(
                selected and selected["revision"] == record["revision"]
                and selected["digest"] == record["digest"]
                and selected["confirmation_current"]
            )
            result.append({
                "catalogue_binding": link,
                "source_observation": source_observation(source, self.binding(source)),
                "source_binding": self.binding(source),
                "datasets": body["datasets"],
                "revision": record["revision"],
                "digest": record["digest"],
                "confirmed_by": str(record["confirming_actor"]),
                "current": current,
            })
            if len(result) > 100:
                raise Rejected("source_association_workspace_bound", 423)
        return result

    def planning(
        self, tenant: str, site: str, expected: int, content_digest: str,
        application: str | None = None, environment: str | None = None,
    ) -> dict[str, Any]:
        # Transport has already authenticated the Planning caller and its delegated actor.
        actor = Actor(identifier(tenant), "", "", "inventory.admin", identifier(site))
        with self.d.database.transaction() as tx:
            requested = tx.one(
                "SELECT payload FROM inventory.migration_reviews "
                "WHERE tenant=%s AND site=%s AND revision=%s",
                (tenant, site, expected),
            )
            review = (
                self.review(tx, actor, requested["payload"]["source_profile_id"])
                if requested
                else None
            )
            if (
                not review
                or review["revision"] != expected
                or review["digest"] != content_digest
                or not review["confirmation_current"]
            ):
                raise Rejected("current_migration_review_required", 409)
            source, target = review["source"], review["target"]
            return {
                "tenant_id": tenant,
                "site_id": site,
                "revision": expected,
                "digest": content_digest,
                **(
                    {"destination": review["input"]["destination"]}
                    if review["input"].get("destination") is not None
                    else {}
                ),
                "method": review["input"]["method"],
                "target_disk_formats": target["facts"]["disk_formats"],
                "source": self.binding(source),
                "target": self.binding(target),
                "source_observation": source_observation(source, self.binding(source)),
                "catalogue_binding": review["input"].get("catalogue_binding"),
                "source_associations": self.source_associations(tx, actor, application, environment)
                if application is not None and environment is not None else [],
                "collection_coverages": self.collection_read(
                    tenant, site, source, target,
                    self.binding(source), self.binding(target), self.d.clock()
                ) if self.collection_read is not None and application is not None
                and environment is not None else [],
                "datasets": review["input"]["datasets"],
                "disks": source["facts"]["disks"],
                "owner_inputs": review["input"]["owner_inputs"],
                "objectives": review["input"]["objectives"],
                "confirmed_by": review["confirmed_by"],
                "current": True,
                "native_write_authorized": False,
            }
