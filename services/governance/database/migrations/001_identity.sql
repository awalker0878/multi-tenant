-- Governance-owned bootstrap state. Run once/replay as governance_migrator.
-- The sentinel is provisioned by migration, never by an application startup.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
CREATE TABLE IF NOT EXISTS app.bootstrap_administrator (
    id smallint PRIMARY KEY CHECK (id = 1),
    state varchar(32) NOT NULL CHECK (state IN ('uninitialized', 'password_change_required', 'local_setup', 'retired')),
    password_hash text,
    credential_version integer NOT NULL DEFAULT 0,
    initialized_at timestamptz,
    password_changed_at timestamptz,
    retired_at timestamptz,
    failed_attempts integer NOT NULL DEFAULT 0,
    locked_until timestamptz,
    CHECK ((state IN ('uninitialized', 'retired') AND password_hash IS NULL)
        OR (state IN ('password_change_required', 'local_setup') AND password_hash IS NOT NULL))
);
INSERT INTO app.bootstrap_administrator (id, state) VALUES (1, 'uninitialized') ON CONFLICT (id) DO NOTHING;
CREATE TABLE IF NOT EXISTS app.identity_sessions (
    token_hash char(64) PRIMARY KEY,
    audience varchar(32) NOT NULL CHECK (audience = 'console'),
    credential_version integer NOT NULL,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz
);
CREATE INDEX IF NOT EXISTS identity_sessions_expiry ON app.identity_sessions (expires_at);
CREATE TABLE IF NOT EXISTS app.identity_audit (
    id uuid PRIMARY KEY,
    actor varchar(64) NOT NULL,
    event varchar(64) NOT NULL,
    occurred_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.identity_outbox (
    id uuid PRIMARY KEY REFERENCES app.identity_audit (id),
    event varchar(64) NOT NULL,
    occurred_at timestamptz NOT NULL,
    published_at timestamptz
);
-- The runtime can change the sentinel, but cannot delete/recreate it or erase audit.
GRANT SELECT, UPDATE ON app.bootstrap_administrator TO governance_runtime;
GRANT SELECT, INSERT, UPDATE ON app.identity_sessions TO governance_runtime;
GRANT SELECT, INSERT ON app.identity_audit TO governance_runtime;
GRANT SELECT, INSERT ON app.identity_outbox TO governance_runtime;
GRANT UPDATE (published_at) ON app.identity_outbox TO governance_runtime;
COMMIT;
