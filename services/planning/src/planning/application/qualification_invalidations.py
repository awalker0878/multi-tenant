"""Durable tenant-scoped Assurance hints, never a grant of native support."""

from typing import Any

from planning.application.ports import Database
from planning.domain.model import Rejected, canonical, digest, identifier, sha, shape

EVENT_KEYS = {
    "event_id",
    "tenant_id",
    "scope_sha256",
    "authority_epoch",
    "operation",
    "state",
    "decision_sha256",
    "event_sha256",
}
OPERATIONS = {
    "publish": "qualified",
    "restore": "qualified",
    "suspend": "suspended",
    "revoke": "revoked",
}


class QualificationInvalidations:
    def __init__(self, database: Database) -> None:
        self.database = database

    def accept(self, event: dict[str, Any]) -> dict[str, Any]:
        """Commit the inbox and conservative plan holds before acknowledging."""
        shape(event, EVENT_KEYS)
        event_id = identifier(event["event_id"])
        tenant = identifier(event["tenant_id"])
        scope_hash = sha(event["scope_sha256"])
        event_hash = sha(event["event_sha256"])
        sha(event["decision_sha256"])
        epoch = event["authority_epoch"]
        if (
            type(epoch) is not int
            or not 1 <= epoch <= 2**53 - 1
            or event["operation"] not in OPERATIONS
            or event["state"] != OPERATIONS[event["operation"]]
        ):
            raise Rejected("invalid_qualification_invalidation")
        fingerprint = digest(event)
        envelope = canonical(event)

        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (scope_hash,))
            prior = tx.one(
                "SELECT payload_sha256 FROM app.planning_qualification_inbox WHERE event_id=%s",
                (event_id,),
            )
            if prior is not None:
                if prior["payload_sha256"] != fingerprint:
                    raise Rejected("invalidation_event_conflict", 409)
            else:
                # One epoch can never represent different events, even if the
                # receiver sees events in an arbitrary transport order.
                collision = tx.one(
                    "SELECT event_id FROM app.planning_qualification_inbox "
                    "WHERE scope_sha256=%s AND authority_epoch=%s",
                    (scope_hash, epoch),
                )
                if collision is not None:
                    raise Rejected("invalidation_epoch_conflict", 409)
                head = tx.one(
                    "SELECT tenant FROM app.planning_qualification_heads WHERE scope_sha256=%s",
                    (scope_hash,),
                )
                if head is not None and str(head["tenant"]) != tenant:
                    raise Rejected("invalidation_scope_conflict", 409)
                tx.execute(
                    "INSERT INTO app.planning_fact_inbox(event_id,tenant,digest,envelope) "
                    "VALUES(%s,%s,%s,%s::jsonb)",
                    (event_id, tenant, fingerprint, envelope),
                )
                tx.execute(
                    "INSERT INTO app.planning_qualification_inbox("
                    "event_id,tenant,scope_sha256,authority_epoch,event_sha256,"
                    "payload_sha256,state) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (event_id, tenant, scope_hash, epoch, event_hash, fingerprint, event["state"]),
                )
                tx.execute(
                    "INSERT INTO app.planning_qualification_heads("
                    "scope_sha256,tenant,authority_epoch,event_sha256,state) "
                    "VALUES(%s,%s,%s,%s,%s) "
                    "ON CONFLICT(scope_sha256) DO UPDATE "
                    "SET authority_epoch=EXCLUDED.authority_epoch, "
                    "event_sha256=EXCLUDED.event_sha256, state=EXCLUDED.state "
                    "WHERE app.planning_qualification_heads.authority_epoch "
                    "< EXCLUDED.authority_epoch",
                    (scope_hash, tenant, epoch, event_hash, event["state"]),
                )
                # An invalidation is only a hint, including publish/restore:
                # never clear an old hold, grant support or modify plan bytes.
                tx.execute(
                    "INSERT INTO app.planning_invalidations(tenant,plan,event_id) "
                    "SELECT tenant,id,%s FROM app.planning_records "
                    "WHERE tenant=%s AND kind='plan'",
                    (event_id, tenant),
                )

        return {
            "persisted": True,
            "event_id": event_id,
            "scope_sha256": scope_hash,
            "authority_epoch": epoch,
            "event_sha256": event_hash,
        }
