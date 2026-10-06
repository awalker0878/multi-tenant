-- P05 local reservation journal. Only controlled owner migrations may alter history.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE lifecycle_owner;
CREATE TABLE app.reservation_heads (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, plan_digest text NOT NULL,
 intent_key text NOT NULL UNIQUE, intent jsonb NOT NULL, receipt jsonb,
 state text NOT NULL CHECK (state IN ('local_intent','attempting','outcome_unknown','reserved','confirmed','expired_held','released','denied')),
 revision bigint NOT NULL CHECK (revision > 0)
);
CREATE TABLE app.reservation_commands (
 tenant uuid NOT NULL, command_key text NOT NULL, payload text NOT NULL,
 reservation uuid NOT NULL REFERENCES app.reservation_heads(id), PRIMARY KEY(tenant,command_key)
);
CREATE TABLE app.reservation_events (
 id uuid PRIMARY KEY, reservation uuid NOT NULL REFERENCES app.reservation_heads(id),
 state text NOT NULL, facts jsonb NOT NULL, occurred_at bigint NOT NULL
);
GRANT SELECT, INSERT, UPDATE ON app.reservation_heads TO lifecycle_runtime;
GRANT SELECT, INSERT ON app.reservation_commands, app.reservation_events TO lifecycle_runtime;
COMMIT;
