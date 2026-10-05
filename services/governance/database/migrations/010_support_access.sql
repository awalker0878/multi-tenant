\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
-- Existing sessions can continue their ordinary lifecycle, but must reauthenticate
-- before exceptional support access can prove their signer against current keys.
ALTER TABLE app.federated_sessions ADD COLUMN IF NOT EXISTS provider_key_sha256 char(64);
ALTER TABLE app.oidc_verifications ADD COLUMN IF NOT EXISTS provider_key_sha256 char(64);
CREATE TABLE IF NOT EXISTS app.support_security_grants (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    actor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    role varchar(16) NOT NULL CHECK (role IN ('approver', 'reviewer')),
    site_id varchar(64) NOT NULL, environment varchar(64) NOT NULL,
    granted_by uuid NOT NULL REFERENCES app.federated_actors(id),
    expires_at timestamptz NOT NULL, created_at timestamptz NOT NULL,
    revoked_at timestamptz,
    revision integer NOT NULL DEFAULT 1,
    CHECK (actor_id <> granted_by)
);
CREATE TABLE IF NOT EXISTS app.support_requests (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    requester_id uuid NOT NULL REFERENCES app.federated_actors(id),
    executor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    binding_json text NOT NULL, binding_sha256 char(64) NOT NULL,
    policy_version integer NOT NULL CHECK (policy_version = 1),
    requester_authority char(64) NOT NULL, requester_session_hash char(64) NOT NULL,
    admission_binding char(64) NOT NULL, console_fingerprint char(64) NOT NULL,
    connection_revision integer NOT NULL,
    state varchar(16) NOT NULL CHECK (state IN ('requested', 'approved', 'active', 'rejected', 'revoked', 'expired', 'invalidated')),
    revision integer NOT NULL,
    expires_at timestamptz NOT NULL, created_at timestamptz NOT NULL,
    executor_session_hash char(64), effective_until timestamptz,
    admission_count integer NOT NULL DEFAULT 0 CHECK (admission_count >= 0)
);
CREATE TABLE IF NOT EXISTS app.support_approvals (
    request_id uuid NOT NULL REFERENCES app.support_requests(id),
    role varchar(16) NOT NULL CHECK (role IN ('tenant', 'security')),
    actor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    authority_sha256 char(64) NOT NULL,
    resources_sha256 char(64) NOT NULL,
    security_grant_id uuid REFERENCES app.support_security_grants(id),
    session_hash char(64) NOT NULL,
    expires_at timestamptz NOT NULL, created_at timestamptz NOT NULL,
    PRIMARY KEY (request_id, role), UNIQUE (request_id, actor_id)
);
CREATE TABLE IF NOT EXISTS app.support_reviews (
    request_id uuid PRIMARY KEY REFERENCES app.support_requests(id),
    actor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    security_grant_id uuid NOT NULL REFERENCES app.support_security_grants(id),
    outcome varchar(16) NOT NULL CHECK (outcome IN ('acceptable', 'incident')),
    case_reference varchar(128) NOT NULL,
    reviewed_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.support_audit (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    actor_id uuid REFERENCES app.federated_actors(id),
    resource_id uuid NOT NULL, revision integer NOT NULL,
    event varchar(64) NOT NULL, correlation_id uuid NOT NULL,
    payload_json text NOT NULL, occurred_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.support_outbox (
    id uuid PRIMARY KEY REFERENCES app.support_audit(id),
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    event varchar(64) NOT NULL, payload_json text NOT NULL,
    occurred_at timestamptz NOT NULL, published_at timestamptz,
    attempts integer NOT NULL DEFAULT 0, available_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_error varchar(32), quarantined_at timestamptz
);
CREATE INDEX IF NOT EXISTS support_requests_expiry ON app.support_requests (expires_at, id) WHERE state IN ('requested', 'approved', 'active');
CREATE INDEX IF NOT EXISTS support_outbox_pending ON app.support_outbox (available_at, occurred_at, id) WHERE published_at IS NULL AND quarantined_at IS NULL;
REVOKE ALL ON app.support_security_grants, app.support_requests, app.support_approvals, app.support_reviews, app.support_audit, app.support_outbox FROM governance_runtime;
GRANT SELECT, INSERT ON app.support_security_grants, app.support_requests, app.support_approvals, app.support_reviews, app.support_audit, app.support_outbox TO governance_runtime;
GRANT UPDATE (revoked_at, revision) ON app.support_security_grants TO governance_runtime;
GRANT UPDATE (state, revision, executor_session_hash, effective_until, admission_count) ON app.support_requests TO governance_runtime;
GRANT UPDATE (published_at, attempts, available_at, last_error, quarantined_at) ON app.support_outbox TO governance_runtime;
COMMIT;
