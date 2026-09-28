-- Tenant-scoped evidence index. Artifact bytes and signed high-water marks live
-- outside PostgreSQL under distinct storage/administration identities.
CREATE TABLE hosting_controlplane.evidence_streams (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    last_sequence bigint NOT NULL DEFAULT 0 CHECK (last_sequence >= 0),
    head_hash text NOT NULL DEFAULT repeat('0', 64)
        CHECK (head_hash ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (organization_id, tenant_id)
);

CREATE TABLE hosting_controlplane.evidence_entries (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    sequence bigint NOT NULL CHECK (sequence > 0),
    event_key text NOT NULL CHECK (event_key ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    evidence_kind text NOT NULL CHECK (evidence_kind IN
        ('OBSERVATION', 'NATIVE_RECEIPT', 'TRANSFER_MANIFEST',
         'VERIFICATION_RESULT', 'RECOVERY_DECISION')),
    subject_id text NOT NULL CHECK (subject_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    blob_digest text NOT NULL CHECK (blob_digest ~ '^[0-9a-f]{64}$'),
    blob_size bigint NOT NULL CHECK (blob_size BETWEEN 2 AND 1048576),
    previous_hash text NOT NULL CHECK (previous_hash ~ '^[0-9a-f]{64}$'),
    entry_hash text NOT NULL CHECK (entry_hash ~ '^[0-9a-f]{64}$'),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, sequence),
    UNIQUE (organization_id, tenant_id, event_key),
    FOREIGN KEY (organization_id, tenant_id)
        REFERENCES hosting_controlplane.evidence_streams
        (organization_id, tenant_id) ON DELETE RESTRICT
);
CREATE INDEX evidence_subject_page ON hosting_controlplane.evidence_entries
    (organization_id, tenant_id, subject_id, sequence);
CREATE TRIGGER evidence_entries_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.evidence_entries
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

ALTER TABLE hosting_controlplane.evidence_streams ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.evidence_streams FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.evidence_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.evidence_entries FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_evidence_streams ON hosting_controlplane.evidence_streams
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY tenant_evidence_entries ON hosting_controlplane.evidence_entries
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
