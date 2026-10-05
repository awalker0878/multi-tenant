-- Catalogue-owned P01 append/outbox migration; controlled migrator only.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE catalogue_owner;
CREATE TABLE app.messaging_facts (
    event_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    record_id text NOT NULL,
    revision bigint NOT NULL CHECK (revision > 0),
    payload text NOT NULL,
    envelope text NOT NULL,
    UNIQUE (tenant_id, record_id, revision)
);
CREATE TABLE app.messaging_outbox (
    event_id uuid PRIMARY KEY REFERENCES app.messaging_facts(event_id),
    envelope text NOT NULL,
    queued_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    published_at timestamptz
);
CREATE INDEX messaging_pending ON app.messaging_outbox(queued_at, event_id) WHERE published_at IS NULL;
GRANT SELECT, INSERT ON app.messaging_facts TO catalogue_runtime;
GRANT SELECT, INSERT, UPDATE ON app.messaging_outbox TO catalogue_runtime;
COMMIT;
