\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
-- Preserve every existing identity fact, including already published records.
ALTER TABLE app.identity_outbox ADD COLUMN IF NOT EXISTS attempts integer NOT NULL DEFAULT 0;
ALTER TABLE app.identity_outbox ADD COLUMN IF NOT EXISTS available_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE app.identity_outbox ADD COLUMN IF NOT EXISTS last_error varchar(32);
ALTER TABLE app.identity_outbox ADD COLUMN IF NOT EXISTS quarantined_at timestamptz;
CREATE INDEX IF NOT EXISTS identity_outbox_pending ON app.identity_outbox (available_at, occurred_at, id) WHERE published_at IS NULL AND quarantined_at IS NULL;
GRANT UPDATE (attempts, available_at, last_error, quarantined_at) ON app.identity_outbox TO governance_runtime;
COMMIT;
