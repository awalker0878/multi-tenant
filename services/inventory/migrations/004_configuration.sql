-- Inventory-owned immutable API evidence, review revisions and confirmations.
BEGIN;
ALTER TABLE inventory.jobs ADD COLUMN IF NOT EXISTS collect_configuration boolean NOT NULL DEFAULT false;
CREATE TABLE IF NOT EXISTS inventory.configuration_facts (
 generation uuid NOT NULL REFERENCES inventory.jobs(id), tenant uuid NOT NULL,
 endpoint uuid NOT NULL REFERENCES inventory.endpoints(id), query text NOT NULL,
 payload jsonb NOT NULL, collected_at double precision NOT NULL,
 expires_at double precision NOT NULL, PRIMARY KEY(generation, query)
);
CREATE TABLE IF NOT EXISTS inventory.porting_revisions (
 tenant uuid NOT NULL, site uuid NOT NULL, revision integer NOT NULL,
 payload jsonb NOT NULL, digest text NOT NULL, actor uuid NOT NULL,
 created_at double precision NOT NULL, PRIMARY KEY(tenant,site,revision)
);
CREATE TABLE IF NOT EXISTS inventory.porting_confirmations (
 tenant uuid NOT NULL, site uuid NOT NULL, revision integer NOT NULL,
 digest text NOT NULL, actor uuid NOT NULL, confirmed_at double precision NOT NULL,
 PRIMARY KEY(tenant,site,revision),
 FOREIGN KEY(tenant,site,revision) REFERENCES inventory.porting_revisions(tenant,site,revision)
);
GRANT SELECT,INSERT ON inventory.configuration_facts, inventory.porting_revisions,
 inventory.porting_confirmations TO inventory_runtime;
COMMIT;
