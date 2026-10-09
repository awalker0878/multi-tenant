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
-- Field-level append-only projection for audit and scoped queries. Its parent
-- signed envelope remains the sole source of evidentiary authority.
CREATE TABLE IF NOT EXISTS inventory.migration_collection_fields (
  envelope_id uuid NOT NULL REFERENCES inventory.migration_collection_receipts(id),
  tenant uuid NOT NULL,
  site uuid NOT NULL,
  scope text NOT NULL CHECK (scope IN ('source','target','owner')),
  attribute_id text NOT NULL,
  evidence_kind text NOT NULL CHECK (evidence_kind IN ('observation','applicability')),
  api_family text,
  api_version text,
  native_operation text,
  value_sha256 char(64) CHECK (value_sha256 IS NULL OR value_sha256 ~ '^[a-f0-9]{64}
GRANT SELECT,INSERT ON inventory.migration_collection_receipts, inventory.migration_collection_fields TO inventory_runtime;
COMMIT;
),
  evidence_sha256 char(64) NOT NULL CHECK (evidence_sha256 ~ '^[a-f0-9]{64}
GRANT SELECT,INSERT ON inventory.migration_collection_receipts TO inventory_runtime;
COMMIT;
),
  observed_at double precision NOT NULL,
  PRIMARY KEY(envelope_id,scope,attribute_id,evidence_kind)
);
CREATE INDEX IF NOT EXISTS migration_collection_fields_history
  ON inventory.migration_collection_fields(tenant,site,scope,attribute_id,observed_at DESC);

-- No UPDATE/DELETE grant: a new signed receipt supersedes but never overwrites.
GRANT SELECT,INSERT ON inventory.migration_collection_receipts TO inventory_runtime;
COMMIT;
