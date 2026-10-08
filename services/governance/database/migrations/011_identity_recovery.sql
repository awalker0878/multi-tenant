\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
CREATE TABLE IF NOT EXISTS app.identity_recovery_receipts (
    id uuid PRIMARY KEY,
    binding_sha256 char(64) UNIQUE NOT NULL,
    plan_sha256 char(64) NOT NULL,
    post_snapshot_sha256 char(64) NOT NULL,
    envelope_json text NOT NULL,
    counts_json text NOT NULL,
    applied_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.identity_recovery_releases (
    id uuid PRIMARY KEY REFERENCES app.identity_recovery_receipts(id),
    envelope_json text NOT NULL,
    envelope_sha256 char(64) NOT NULL,
    confirmed_at timestamptz NOT NULL
);
REVOKE ALL ON app.identity_recovery_receipts, app.identity_recovery_releases FROM governance_runtime;
GRANT SELECT ON app.identity_recovery_receipts, app.identity_recovery_releases TO governance_runtime;
REVOKE UPDATE (binding_sha256) ON app.identity_admission FROM governance_runtime;
-- BEGIN POSTGRES RECOVERY FUNCTION
CREATE OR REPLACE FUNCTION app.bind_initial_identity_admission(binding text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
BEGIN
    IF binding IS NULL OR binding !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'identity_recovery_held' USING ERRCODE = '42501';
    END IF;
    PERFORM id FROM app.bootstrap_administrator WHERE id = 1 FOR UPDATE;
    UPDATE app.identity_admission SET binding_sha256 = binding
      WHERE id = 1 AND binding_sha256 IS NULL
      AND EXISTS (SELECT 1 FROM app.bootstrap_administrator WHERE id = 1 AND state = 'uninitialized');
    IF NOT FOUND THEN
        RAISE EXCEPTION 'identity_recovery_held' USING ERRCODE = '42501';
    END IF;
END;
$body$;
REVOKE ALL ON FUNCTION app.bind_initial_identity_admission(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.bind_initial_identity_admission(text) TO governance_runtime;
-- END POSTGRES RECOVERY FUNCTION
COMMIT;
