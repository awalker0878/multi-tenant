\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
-- Installation identity commands retain digests only, never bearer credentials.
CREATE TABLE IF NOT EXISTS app.identity_command_keys (
    scope_sha256 char(64) NOT NULL,
    key_sha256 char(64) NOT NULL,
    request_sha256 char(64) NOT NULL,
    expires_at timestamptz NOT NULL,
    PRIMARY KEY (scope_sha256, key_sha256)
);
CREATE INDEX IF NOT EXISTS identity_command_keys_expiry ON app.identity_command_keys(expires_at);
REVOKE ALL ON app.identity_command_keys FROM governance_runtime;
GRANT SELECT, INSERT, DELETE ON app.identity_command_keys TO governance_runtime;
COMMIT;
