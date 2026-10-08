-- Immutable operator input drafts are tenant/site scoped and confer no native authority.
BEGIN;
CREATE TABLE IF NOT EXISTS inventory.operator_input_revisions (
 tenant uuid NOT NULL, site uuid NOT NULL, revision integer NOT NULL,
 payload jsonb NOT NULL, digest text NOT NULL, actor uuid NOT NULL,
 created_at double precision NOT NULL, PRIMARY KEY(tenant,site,revision)
);
GRANT SELECT,INSERT ON inventory.operator_input_revisions TO inventory_runtime;
COMMIT;
