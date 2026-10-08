\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE governance_owner;
CREATE INDEX IF NOT EXISTS membership_directory_position ON app.tenant_memberships (tenant_id, id);
CREATE INDEX IF NOT EXISTS actor_directory_position ON app.tenant_memberships (actor_id, state, tenant_id);
COMMIT;
