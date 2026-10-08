\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
CREATE TABLE IF NOT EXISTS app.actor_delegations (
    id uuid UNIQUE NOT NULL,
    token_hash char(64) PRIMARY KEY,
    session_hash char(64) NOT NULL REFERENCES app.federated_sessions(token_hash),
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    actor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    audience varchar(32) NOT NULL CHECK (audience IN ('catalogue', 'planning', 'assurance')),
    action varchar(64) NOT NULL,
    scope_json text NOT NULL,
    authority_fingerprint char(64) NOT NULL,
    service_fingerprint char(64) NOT NULL,
    console_fingerprint char(64) NOT NULL,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz
);
CREATE TABLE IF NOT EXISTS app.delegation_audit (
    id uuid PRIMARY KEY,
    delegation_id uuid NOT NULL REFERENCES app.actor_delegations(id),
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    actor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    event varchar(32) NOT NULL CHECK (event IN ('issued', 'revoked')),
    occurred_at timestamptz NOT NULL
);
REVOKE ALL ON app.actor_delegations, app.delegation_audit FROM governance_runtime;
GRANT SELECT, INSERT ON app.actor_delegations, app.delegation_audit TO governance_runtime;
GRANT UPDATE (revoked_at) ON app.actor_delegations TO governance_runtime;
COMMIT;
