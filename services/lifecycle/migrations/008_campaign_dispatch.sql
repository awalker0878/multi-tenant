\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE lifecycle_owner;
CREATE SEQUENCE app.migration_dispatch_order;
ALTER TABLE app.migration_members ADD COLUMN considered_order bigint NOT NULL DEFAULT 0;
GRANT USAGE ON SEQUENCE app.migration_dispatch_order TO lifecycle_runtime;
CREATE INDEX migration_dispatch_pending ON app.migration_members(state,considered_order);
COMMIT;
