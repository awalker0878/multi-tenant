-- Planning-owned P01 inbox/projection migration; controlled migrator only.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE planning_owner;
CREATE TABLE app.messaging_inbox (
    event_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    envelope_sha256 text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE app.messaging_heads (
    tenant_id text NOT NULL,
    record_id text NOT NULL,
    revision bigint NOT NULL,
    PRIMARY KEY(tenant_id, record_id)
);
CREATE TABLE app.messaging_projection (
    tenant_id text NOT NULL,
    record_id text NOT NULL,
    revision bigint NOT NULL CHECK(revision > 0),
    payload_sha256 text NOT NULL,
    event_id uuid NOT NULL UNIQUE REFERENCES app.messaging_inbox(event_id),
    PRIMARY KEY(tenant_id, record_id, revision)
);
GRANT SELECT, INSERT ON app.messaging_inbox, app.messaging_projection TO planning_runtime;
GRANT SELECT, INSERT, UPDATE ON app.messaging_heads TO planning_runtime;
COMMIT;
