-- External recovery generation is deployment custody, never restored application authority.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
CREATE TABLE IF NOT EXISTS app.identity_admission (
    id smallint PRIMARY KEY CHECK (id = 1),
    binding_sha256 char(64)
);
INSERT INTO app.identity_admission (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
REVOKE ALL ON app.identity_admission FROM governance_runtime;
GRANT SELECT, UPDATE (binding_sha256) ON app.identity_admission TO governance_runtime;
COMMIT;
