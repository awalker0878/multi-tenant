\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE assurance_owner;
CREATE TABLE IF NOT EXISTS app.qualification_command_keys (
    scope_sha256 char(64) NOT NULL,
    key_sha256 char(64) NOT NULL,
    request_sha256 char(64) NOT NULL,
    created_at bigint NOT NULL,
    expires_at bigint NOT NULL,
    PRIMARY KEY (scope_sha256, key_sha256)
);
REVOKE ALL ON app.qualification_command_keys FROM assurance_runtime;
GRANT SELECT, INSERT, DELETE ON app.qualification_command_keys TO assurance_runtime;
COMMIT;
