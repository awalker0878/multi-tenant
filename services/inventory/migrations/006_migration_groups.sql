-- Inventory owns durable migration selections; no native execution authority.
BEGIN;
CREATE TABLE IF NOT EXISTS inventory.migration_groups (
 id uuid NOT NULL, tenant uuid NOT NULL, site uuid NOT NULL, revision integer NOT NULL,
 payload jsonb NOT NULL, digest text NOT NULL, actor uuid NOT NULL,
 created_at double precision NOT NULL, PRIMARY KEY(tenant,site,id,revision)
);
CREATE INDEX IF NOT EXISTS migration_groups_scope ON inventory.migration_groups(tenant,site,id,revision DESC);
GRANT SELECT,INSERT ON inventory.migration_groups TO inventory_runtime;
COMMIT;
