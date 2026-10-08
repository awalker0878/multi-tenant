\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
CREATE TABLE IF NOT EXISTS app.approvals (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES app.tenants(id),
    plan_id uuid NOT NULL,
    plan_revision integer NOT NULL,
    plan_digest char(64) NOT NULL,
    binding_json text NOT NULL,
    requester_id uuid NOT NULL REFERENCES app.federated_actors(id),
    request_authority char(64) NOT NULL,
    decision_authority char(64),
    policy_version integer NOT NULL DEFAULT 1 CHECK (policy_version = 1),
    state varchar(16) NOT NULL CHECK (state IN ('requested', 'approved', 'rejected', 'revoked', 'expired')),
    revision integer NOT NULL,
    expires_at timestamptz NOT NULL,
    decided_by uuid REFERENCES app.federated_actors(id),
    created_at timestamptz NOT NULL
);
REVOKE ALL ON app.approvals FROM governance_runtime;
GRANT SELECT, INSERT ON app.approvals TO governance_runtime;
GRANT UPDATE (state, revision, decided_by, decision_authority) ON app.approvals TO governance_runtime;
COMMIT;
