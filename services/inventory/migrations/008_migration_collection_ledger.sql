-- Inventory-owned immutable signed collection receipts and per-field projections.
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
  observed_at double precision NOT NULL,
  generation_sequence bigint NOT NULL CHECK (generation_sequence >= 1),
  expires_at double precision NOT NULL,
  revoked_at double precision,
  UNIQUE (tenant,site,source_profile,target_profile,envelope_sha256)
);
CREATE INDEX IF NOT EXISTS migration_collection_receipts_current
  ON inventory.migration_collection_receipts (
    tenant,site,source_profile,target_profile,generation_sequence DESC,observed_at DESC,id DESC
  );
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
  evidence_sha256 char(64) NOT NULL CHECK (evidence_sha256 ~ '^[a-f0-9]{64}$'),
  observed_at double precision NOT NULL,
  PRIMARY KEY (envelope_id,scope,attribute_id,evidence_kind)
);
CREATE INDEX IF NOT EXISTS migration_collection_fields_history
  ON inventory.migration_collection_fields (tenant,site,scope,attribute_id,observed_at DESC);
-- Runtime can append observations but cannot retroactively change or erase them.
GRANT SELECT,INSERT ON inventory.migration_collection_receipts,
  inventory.migration_collection_fields TO inventory_runtime;
COMMIT;
),
  source_response_sha256 char(64) CHECK (
    source_response_sha256 IS NULL OR source_response_sha256 ~ '^[a-f0-9]{64}
  evidence_sha256 char(64) NOT NULL CHECK (evidence_sha256 ~ '^[a-f0-9]{64}$'),
  observed_at double precision NOT NULL,
  PRIMARY KEY (envelope_id,scope,attribute_id,evidence_kind)
);
CREATE INDEX IF NOT EXISTS migration_collection_fields_history
  ON inventory.migration_collection_fields (tenant,site,scope,attribute_id,observed_at DESC);
-- Runtime can append observations but cannot retroactively change or erase them.
GRANT SELECT,INSERT ON inventory.migration_collection_receipts,
  inventory.migration_collection_fields TO inventory_runtime;
COMMIT;

  ),
  evidence_sha256 char(64) NOT NULL CHECK (evidence_sha256 ~ '^[a-f0-9]{64}$'),
  observed_at double precision NOT NULL,
  PRIMARY KEY (envelope_id,scope,attribute_id,evidence_kind)
);
CREATE INDEX IF NOT EXISTS migration_collection_fields_history
  ON inventory.migration_collection_fields (tenant,site,scope,attribute_id,observed_at DESC);
-- Runtime can append observations but cannot retroactively change or erase them.
GRANT SELECT,INSERT ON inventory.migration_collection_receipts,
  inventory.migration_collection_fields TO inventory_runtime;
COMMIT;
