\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE lifecycle_owner;
ALTER TABLE app.native_projection DROP CONSTRAINT native_projection_state_check;
ALTER TABLE app.native_projection ADD CONSTRAINT native_projection_state_check
 CHECK(state IN ('prepared','running','held','active','retired','stopped',
                'rehearsed','migrated','recovered','cleaned'));
-- Commit the first POSSIBLE business-write boundary with grant redemption, before effect.
-- Runtime cannot erase it. Restored journals require independent custody reconciliation.
CREATE TABLE app.native_migration_writes (
 job uuid PRIMARY KEY REFERENCES app.native_jobs(id),
 operation uuid NOT NULL UNIQUE REFERENCES app.native_operations(id),
 occurred_at bigint NOT NULL
);
GRANT SELECT,INSERT ON app.native_migration_writes TO lifecycle_runtime;
COMMIT;
