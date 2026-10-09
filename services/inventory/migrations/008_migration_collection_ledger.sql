-- Durable Inventory custody for independently signed per-field collection receipts.
-- Immutable history; current reads always choose the newest scoped envelope.
BEGIN;
CREATE TABLE IF NOT EXISTS inventory.migration_collection_receipts (
  id uuid PRIMARY KEY,
  tenant uuid NOT NULL,
  site uuid NOT NULL,
  source_profile uuid NOT NULL REFERENCES inventory.workload_profiles(id),
  target_profile uuid NOT NULL REFERENCES inventory.workload_profiles(id),
  source_sha256 char(64) NOT NULL CHECK (source_sha256 ~ '^[a-f0-9]{64}$'),
  target_sha256 char(64) NOT NULL CHECK (target_sha256 ~ '^[a-f0-9]{64}$'),
  envelope_sha256 char(64) NOT NULL CHECK (envelope_sha256 ~ '^[a-f0-9]{64}$'),
  envelope jsonb NOT NULL,
  publisher text NOT NULL,
  received_at double precision NOT NULL,
  expires_at double precision NOT NULL,
  UNIQUE(tenant,site,source_profile,target_profile,envelope_sha256)
);
CREATE INDEX IF NOT EXISTS migration_collection_receipts_current
  ON inventory.migration_collection_receipts (
    tenant,site,source_profile,target_profile,received_at DESC,id DESC
  );
-- No UPDATE/DELETE grant: a new signed receipt supersedes but never overwrites.
GRANT SELECT,INSERT ON inventory.migration_collection_receipts TO inventory_runtime;
COMMIT;
