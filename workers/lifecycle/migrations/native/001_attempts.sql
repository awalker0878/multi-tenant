-- P07 worker-local effect journal. Apply as the separately administered native owner.
-- This schema does not confer Lifecycle admission, OpenStack or backend authority.
CREATE SCHEMA IF NOT EXISTS native;

CREATE TABLE native.attempts (
    operation_id uuid PRIMARY KEY,
    attempt_id uuid NOT NULL UNIQUE,
    tenant_id uuid NOT NULL,
    fingerprint text NOT NULL CHECK (fingerprint ~ '^[a-f0-9]{64}$'),
    binding jsonb NOT NULL,
    claimed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE native.workspace_holds (
    state_lineage uuid PRIMARY KEY,
    operation_id uuid NOT NULL UNIQUE REFERENCES native.attempts(operation_id),
    held_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE native.events (
    sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id uuid NOT NULL REFERENCES native.attempts(operation_id),
    kind text NOT NULL CHECK (kind IN (
        'prepared', 'apply_started', 'process_exited', 'outcome_unknown', 'readback'
    )),
    facts jsonb NOT NULL CHECK (octet_length(facts::text) <= 262144),
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

REVOKE ALL ON SCHEMA native FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA native FROM PUBLIC;
-- Runtime has INSERT/SELECT only. No lease expiry or restart deletes a native hold.
GRANT USAGE ON SCHEMA native TO native_runtime;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA native TO native_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA native TO native_runtime;
