"""Inventory custody for append-only independently signed field receipts.

Ingesting an envelope proves its signature, tenant/site, exact current native
generations and installed namespace tuple. It never grants E3/E4, equivalence,
or an executable instruction. Current reads never fall back to older receipts.
"""
from typing import Any
from uuid import uuid4

from inventory.application.discovery import Discovery
from inventory.application.workload import WorkloadProfiles
from inventory.domain.discovery import Actor, Rejected, Worker, canonical, digest, identifier, shape
from inventory.infrastructure.migration_collection_evidence import read_collection_coverages


class MigrationCollectionLedger:
    def __init__(self, discovery: Discovery) -> None:
        self.d = discovery
        self.profiles = WorkloadProfiles(discovery)

    def publish(self, worker: Worker, body: dict[str, Any]) -> dict[str, Any]:
        shape(body, {
            "tenant_id", "site_id", "source_profile_id", "target_profile_id", "envelope",
        })
        tenant, site = identifier(body["tenant_id"]), identifier(body["site_id"])
        source_id, target_id = identifier(body["source_profile_id"]), identifier(body["target_profile_id"])
        envelope = body["envelope"]
        if not isinstance(envelope, dict) or len(canonical(envelope).encode()) > 524288:
            raise Rejected("migration_collection_envelope_invalid")
        actor = Actor(tenant, worker.identity, "", "inventory.admin", site)
        with self.d.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7404001)")
            source = self.profiles.profile(tx, actor, source_id)
            target = self.profiles.profile(tx, actor, target_id)
            if (source["profile_type"] != "SourceWorkloadProfile"
                    or target["profile_type"] != "TargetCapabilityProfile"
                    or not source["current"] or not target["current"]):
                raise Rejected("migration_collection_profiles_not_current", 423)
            enrolled = self.d.endpoint(tx, actor, source["endpoint_id"])
            policy = self.d.policy(enrolled)
            if (policy.worker, policy.worker_fingerprint) != (
                    worker.identity, worker.fingerprint):
                raise Rejected("migration_collection_unenrolled_publisher", 403)
            left, right = self.profiles.binding(source), self.profiles.binding(target)
            coverage = read_collection_coverages(
                tenant, site, source, target, left, right, self.d.clock(),
                signed_envelope=envelope,
            )
            if len(coverage) != 3:
                raise Rejected("migration_collection_signature_or_scope_invalid", 423)
            # Even an incomplete signed observation is retained for diagnostics;
            # no field status is promoted merely because ingestion succeeded.
            envelope_sha = digest(envelope)
            tx.execute(
                "INSERT INTO inventory.migration_collection_receipts "
                "(id,tenant,site,source_profile,target_profile,source_sha256,"
                "target_sha256,envelope_sha256,envelope,publisher,received_at,expires_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s) "
                "ON CONFLICT DO NOTHING",
                (
                    str(uuid4()), tenant, site, source_id, target_id,
                    left["profile_sha256"], right["profile_sha256"],
                    envelope_sha, canonical(envelope), worker.identity,
                    self.d.clock(), envelope["payload"]["expires_at"],
                ),
            )
            self.d.record(
                tx, tenant, worker.identity, "migration.collection.receipt",
                source_id,
                {"source_profile_id": source_id, "target_profile_id": target_id,
                 "envelope_sha256": envelope_sha,
                 "status": "complete" if all(x["status"] == "complete" for x in coverage)
                 else "held"},
            )
            return {
                "envelope_sha256": envelope_sha,
                "status": "recorded",
                "coverage": [{"scope": x["scope"], "status": x["status"],
                              "holds": x["holds"]} for x in coverage],
                "native_write_authorized": False,
            }

    def read(
        self, tenant: str, site: str, source: dict[str, Any], target: dict[str, Any],
        source_binding: dict[str, Any], target_binding: dict[str, Any], now: int,
    ) -> list[dict[str, Any]]:
        if not source.get("current") or not target.get("current"):
            return []
        with self.d.database.transaction() as tx:
            records = tx.all(
                "SELECT envelope,source_sha256,target_sha256 FROM "
                "inventory.migration_collection_receipts "
                "WHERE tenant=%s AND site=%s AND source_profile=%s "
                "AND target_profile=%s ORDER BY received_at DESC,id DESC LIMIT 1",
                (identifier(tenant), identifier(site), source["id"], target["id"]),
            )
        if len(records) != 1:
            return []
        record = records[0]
        if (record["source_sha256"] != source_binding["profile_sha256"]
                or record["target_sha256"] != target_binding["profile_sha256"]):
            return []
        return read_collection_coverages(
            tenant, site, source, target, source_binding, target_binding, now,
            signed_envelope=record["envelope"],
        )
