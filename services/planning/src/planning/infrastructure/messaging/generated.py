"""Generated scalar DTO; validate the wire schema before constructing."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedEvent:
    event_type: str
    schema_version: int
    event_id: str
    correlation_id: str
    tenant_id: str
    actor_id: str
    record_id: str
    revision: str
    payload_sha256: str
    source_revision: str
    occurred_at: str
