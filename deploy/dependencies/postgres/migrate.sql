-- Connect over verified TLS as <service>_migrator and supply psql variables:
-- owner=<service>_owner and runtime=<service>_runtime.
-- This fixture is tenant-keyed; it does not implement tenant authorization or RLS.
\set ON_ERROR_STOP on
\set ECHO none
\set VERBOSITY terse
BEGIN;
SET LOCAL ROLE :"owner";

-- A replay of this migration is allowed only for the exact existing version.
-- Refuse empty, newer, older or multiple metadata rows instead of repairing them.
DO $foundation$
BEGIN
    IF session_user <> current_database() || '_migrator'
        OR current_user <> current_database() || '_owner' THEN
        RAISE EXCEPTION 'foundation migration identity mismatch';
    END IF;
    IF to_regclass('app.foundation_schema') IS NOT NULL THEN
        IF (SELECT count(*) FROM app.foundation_schema) <> 1
            OR (SELECT max(version) FROM app.foundation_schema) IS DISTINCT FROM 1 THEN
            RAISE EXCEPTION 'foundation schema version mismatch';
        END IF;
    END IF;
END;
$foundation$;

CREATE TABLE IF NOT EXISTS app.foundation_schema (
    version integer PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS app.foundation_records (
    tenant_id text NOT NULL,
    record_id text NOT NULL,
    payload text NOT NULL,
    PRIMARY KEY (tenant_id, record_id)
);

INSERT INTO app.foundation_schema(version) VALUES (1) ON CONFLICT (version) DO NOTHING;
REVOKE ALL ON app.foundation_schema FROM :"runtime";
GRANT SELECT ON app.foundation_schema TO :"runtime";
GRANT SELECT, INSERT, UPDATE, DELETE ON app.foundation_records TO :"runtime";

INSERT INTO app.foundation_records(tenant_id, record_id, payload) VALUES
    ('tenant_a', 'fixture1', 'synthetic-permit-desk-tenant-a'),
    ('tenant_b', 'fixture1', 'synthetic-permit-desk-tenant-b')
ON CONFLICT (tenant_id, record_id) DO NOTHING;

COMMIT;
SET ROLE :"owner";
SELECT current_database() AS database, session_user AS migration_identity,
    (SELECT version FROM app.foundation_schema) AS schema_version;
RESET ROLE;
