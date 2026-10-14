\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
-- A bounded at-most-once issuance ledger: never store or replay the bearer token.
CREATE TABLE app.delegation_command_keys (
    session_hash char(64) NOT NULL REFERENCES app.federated_sessions(token_hash),
    key_hash char(64) NOT NULL,
    request_sha256 char(64) NOT NULL,
    grant_id uuid NOT NULL REFERENCES app.actor_delegations(id),
    expires_at timestamptz NOT NULL,
    PRIMARY KEY (session_hash, key_hash)
);
CREATE INDEX delegation_command_keys_expiry ON app.delegation_command_keys(expires_at);
REVOKE ALL ON app.delegation_command_keys FROM governance_runtime;
GRANT SELECT, INSERT, DELETE ON app.delegation_command_keys TO governance_runtime;
COMMIT;
