\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
-- Null identifies a system transition; no synthetic federated actor is created.
ALTER TABLE app.governance_audit ALTER COLUMN actor_id DROP NOT NULL;
ALTER TABLE app.governance_outbox ADD COLUMN IF NOT EXISTS attempts integer NOT NULL DEFAULT 0;
ALTER TABLE app.governance_outbox ADD COLUMN IF NOT EXISTS available_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE app.governance_outbox ADD COLUMN IF NOT EXISTS last_error varchar(32);
ALTER TABLE app.governance_outbox ADD COLUMN IF NOT EXISTS quarantined_at timestamptz;
CREATE INDEX IF NOT EXISTS governance_outbox_pending ON app.governance_outbox (available_at, occurred_at, id) WHERE published_at IS NULL AND quarantined_at IS NULL;
CREATE INDEX IF NOT EXISTS approvals_expiry ON app.approvals (expires_at, id) WHERE state IN ('requested', 'approved');
GRANT UPDATE (attempts, available_at, last_error, quarantined_at) ON app.governance_outbox TO governance_runtime;
COMMIT;
