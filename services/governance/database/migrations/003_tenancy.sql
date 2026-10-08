\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
CREATE TABLE IF NOT EXISTS app.tenants (
    id uuid PRIMARY KEY,
    name varchar(200) NOT NULL,
    state varchar(16) NOT NULL CHECK (state IN ('active', 'suspended')),
    revision integer NOT NULL,
    created_by uuid NOT NULL REFERENCES app.federated_actors(id),
    created_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.tenant_memberships (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    actor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    role varchar(32) NOT NULL CHECK (role IN ('tenant_admin', 'author', 'reviewer', 'operator', 'reader')),
    site_id varchar(64), environment varchar(64),
    state varchar(16) NOT NULL CHECK (state IN ('active', 'revoked')),
    expires_at timestamptz,
    revision integer NOT NULL,
    UNIQUE (tenant_id, actor_id)
);
CREATE TABLE IF NOT EXISTS app.delegated_grants (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    membership_id uuid NOT NULL REFERENCES app.tenant_memberships(id),
    membership_revision integer NOT NULL,
    action varchar(64) NOT NULL,
    site_id varchar(64), environment varchar(64), resource_id varchar(128),
    expires_at timestamptz NOT NULL,
    revision integer NOT NULL,
    revoked_at timestamptz,
    created_by uuid NOT NULL REFERENCES app.federated_actors(id)
);
CREATE TABLE IF NOT EXISTS app.tenant_quotas (
    tenant_id uuid PRIMARY KEY REFERENCES app.tenants(id),
    revision integer NOT NULL,
    limits_json text NOT NULL
);
CREATE TABLE IF NOT EXISTS app.governance_commands (
    scope_id varchar(64) NOT NULL,
    actor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    command varchar(64) NOT NULL,
    request_key varchar(128) NOT NULL,
    digest char(64) NOT NULL,
    result_json text NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (scope_id, actor_id, command, request_key)
);
CREATE TABLE IF NOT EXISTS app.governance_audit (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    actor_id uuid NOT NULL REFERENCES app.federated_actors(id),
    event varchar(64) NOT NULL,
    resource_id varchar(128) NOT NULL,
    revision integer NOT NULL,
    payload_json text NOT NULL,
    occurred_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.governance_outbox (
    id uuid PRIMARY KEY REFERENCES app.governance_audit(id),
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    event varchar(64) NOT NULL,
    payload_json text NOT NULL,
    occurred_at timestamptz NOT NULL,
    published_at timestamptz
);
REVOKE ALL ON app.tenants, app.tenant_memberships, app.delegated_grants, app.tenant_quotas,
    app.governance_commands, app.governance_audit, app.governance_outbox FROM governance_runtime;
GRANT SELECT, INSERT, UPDATE ON app.tenants, app.tenant_memberships, app.delegated_grants, app.tenant_quotas TO governance_runtime;
GRANT SELECT, INSERT ON app.governance_commands, app.governance_audit, app.governance_outbox TO governance_runtime;
GRANT UPDATE (published_at) ON app.governance_outbox TO governance_runtime;
COMMIT;
