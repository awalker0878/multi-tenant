-- Governance-owned, revisioned OIDC application settings and opaque authority.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
CREATE TABLE IF NOT EXISTS app.oidc_installation (
    id smallint PRIMARY KEY CHECK (id = 1),
    latest_revision integer NOT NULL DEFAULT 0,
    active_revision integer
);
INSERT INTO app.oidc_installation (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
CREATE TABLE IF NOT EXISTS app.identity_secrets (
    id uuid PRIMARY KEY,
    ciphertext text NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.oidc_connections (
    revision integer PRIMARY KEY,
    issuer varchar(2048) NOT NULL,
    client_id varchar(255) NOT NULL,
    secret_ref uuid NOT NULL REFERENCES app.identity_secrets(id),
    redirect_uri varchar(2048) NOT NULL,
    administrator_subject varchar(255) NOT NULL,
    private_networks text NOT NULL DEFAULT '[]',
    created_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.federated_actors (
    id uuid PRIMARY KEY,
    issuer varchar(2048) NOT NULL,
    subject varchar(255) NOT NULL,
    disabled_at timestamptz,
    UNIQUE (issuer, subject)
);
CREATE TABLE IF NOT EXISTS app.federated_sessions (
    token_hash char(64) PRIMARY KEY,
    actor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    connection_revision integer NOT NULL REFERENCES app.oidc_connections(revision),
    audience varchar(32) NOT NULL CHECK (audience = 'console'),
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz
);
CREATE TABLE IF NOT EXISTS app.oidc_flows (
    state_hash char(64) PRIMARY KEY,
    browser_hash char(64) NOT NULL,
    initiator_hash char(64),
    purpose varchar(16) NOT NULL CHECK (purpose IN ('setup', 'login')),
    connection_revision integer NOT NULL REFERENCES app.oidc_connections(revision),
    protected_context text NOT NULL,
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz
);
CREATE TABLE IF NOT EXISTS app.oidc_verifications (
    proof_hash char(64) PRIMARY KEY,
    initiator_hash char(64) NOT NULL,
    actor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    connection_revision integer NOT NULL REFERENCES app.oidc_connections(revision),
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz
);
REVOKE ALL ON app.oidc_installation, app.identity_secrets, app.oidc_connections,
    app.federated_actors, app.federated_sessions, app.oidc_flows, app.oidc_verifications FROM governance_runtime;
GRANT SELECT, UPDATE ON app.oidc_installation TO governance_runtime;
GRANT SELECT, INSERT ON app.identity_secrets, app.oidc_connections TO governance_runtime;
GRANT SELECT, INSERT, UPDATE ON app.federated_actors, app.federated_sessions,
    app.oidc_flows, app.oidc_verifications TO governance_runtime;
COMMIT;
