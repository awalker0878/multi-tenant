"""Commit deduplication and an owner-local projection as a single transaction."""

import hashlib

import psycopg

from planning.infrastructure.messaging.codec import canonical, decode


class Inbox:
    def __init__(self, database: psycopg.Connection[tuple[object, ...]]) -> None:
        self.database = database

    def accept(self, wire: bytes, producer: str, tenants: frozenset[str]) -> str:
        event = decode(wire)
        if producer != "catalogue" or event.tenant_id not in tenants:
            raise ValueError("event_scope_denied")
        digest = hashlib.sha256(canonical(event)).hexdigest()
        with self.database.transaction():
            self.database.execute("SET LOCAL statement_timeout = '3s'")
            row = self.database.execute(
                "INSERT INTO app.messaging_inbox(event_id, tenant_id, envelope_sha256) "
                "VALUES (%s,%s,%s) ON CONFLICT (event_id) DO NOTHING RETURNING event_id",
                (event.event_id, event.tenant_id, digest),
            ).fetchone()
            if row is None:
                prior = self.database.execute(
                    "SELECT tenant_id,envelope_sha256 FROM app.messaging_inbox WHERE event_id=%s",
                    (event.event_id,),
                ).fetchone()
                if prior != (event.tenant_id, digest):
                    raise ValueError("event_identity_conflict")
                return "duplicate"
            identity = (event.tenant_id, event.record_id)
            self.database.execute(
                "INSERT INTO app.messaging_heads(tenant_id,record_id,revision) VALUES (%s,%s,0) "
                "ON CONFLICT DO NOTHING",
                identity,
            )
            head = self.database.execute(
                "SELECT revision FROM app.messaging_heads WHERE tenant_id=%s AND record_id=%s "
                "FOR UPDATE",
                identity,
            ).fetchone()
            if head is None or int(event.revision) != int(str(head[0])) + 1:
                raise ValueError("revision_gap_or_stale")
            self.database.execute(
                "INSERT INTO app.messaging_projection "
                "(tenant_id,record_id,revision,payload_sha256,event_id) VALUES (%s,%s,%s,%s,%s)",
                (*identity, event.revision, event.payload_sha256, event.event_id),
            )
            self.database.execute(
                "UPDATE app.messaging_heads SET revision=%s WHERE tenant_id=%s AND record_id=%s",
                (event.revision, *identity),
            )
        return "projected"
