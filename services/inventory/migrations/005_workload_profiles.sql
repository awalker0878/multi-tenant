-- Immutable native profile generations and separately attributed owner reviews.
BEGIN;
ALTER TABLE inventory.jobs ADD COLUMN IF NOT EXISTS profile_reads integer NOT NULL DEFAULT 0;
CREATE TABLE IF NOT EXISTS inventory.workload_profiles (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, endpoint uuid NOT NULL REFERENCES inventory.endpoints(id),
 generation uuid NOT NULL REFERENCES inventory.jobs(id), native_id text NOT NULL,
 profile_type text NOT NULL CHECK (profile_type IN ('SourceWorkloadProfile','TargetCapabilityProfile')),
 payload jsonb NOT NULL, digest text NOT NULL, policy_digest text NOT NULL,
 collected_at double precision NOT NULL, expires_at double precision NOT NULL,
 UNIQUE(generation,profile_type,native_id)
);
CREATE TABLE IF NOT EXISTS inventory.migration_reviews (
 tenant uuid NOT NULL, site uuid NOT NULL, revision integer NOT NULL,
 payload jsonb NOT NULL, digest text NOT NULL, actor uuid NOT NULL,
 created_at double precision NOT NULL, PRIMARY KEY(tenant,site,revision)
);
CREATE TABLE IF NOT EXISTS inventory.migration_confirmations (
 tenant uuid NOT NULL, site uuid NOT NULL, revision integer NOT NULL,
 digest text NOT NULL, actor uuid NOT NULL, confirmed_at double precision NOT NULL,
 PRIMARY KEY(tenant,site,revision),
 FOREIGN KEY(tenant,site,revision) REFERENCES inventory.migration_reviews(tenant,site,revision)
);
GRANT SELECT,INSERT ON inventory.workload_profiles, inventory.migration_reviews,
 inventory.migration_confirmations TO inventory_runtime;
COMMIT;
