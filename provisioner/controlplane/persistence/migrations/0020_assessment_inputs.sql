-- Internal signed evidence only. Runtime API receives SELECT; a separate
-- NOSUPERUSER/NOBYPASSRLS ingestion login receives SELECT/INSERT explicitly.
-- No role is created or granted access by this migration.
CREATE TABLE hosting_controlplane.assessment_inputs (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    evidence_id text NOT NULL CHECK
        (evidence_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    kind text NOT NULL CHECK (kind IN ('INSTALLATION', 'ROUTE', 'CONTROL')),
    binding_digest text NOT NULL CHECK (binding_digest ~ '^[0-9a-f]{64}$'),
    revision bigint NOT NULL CHECK (revision > 0),
    evidence_json text NOT NULL CHECK
        (octet_length(evidence_json) <= 65536
         AND jsonb_typeof(evidence_json::jsonb) = 'object'),
    evidence_digest text NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
    signatures_json text NOT NULL CHECK
        (octet_length(signatures_json) <= 2048
         AND jsonb_typeof(signatures_json::jsonb) = 'array'
         AND jsonb_array_length(signatures_json::jsonb) BETWEEN 1 AND 2),
    policy_json text NOT NULL CHECK
        (octet_length(policy_json) <= 1048576
         AND jsonb_typeof(policy_json::jsonb) = 'object'),
    policy_signature text NOT NULL CHECK (length(policy_signature) = 88),
    policy_revision bigint NOT NULL CHECK (policy_revision > 0),
    policy_digest text NOT NULL CHECK (policy_digest ~ '^[0-9a-f]{64}$'),
    verified_at timestamptz NOT NULL,
    verified_subjects text[] NOT NULL CHECK (cardinality(verified_subjects) BETWEEN 1 AND 2),
    persisted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, evidence_id),
    UNIQUE (organization_id, tenant_id, kind, binding_digest, revision),
    CHECK (evidence_json::jsonb ->> 'evidenceId' = evidence_id),
    CHECK (evidence_json::jsonb ->> 'kind' = kind),
    CHECK ((evidence_json::jsonb ->> 'revision')::bigint = revision)
);
CREATE INDEX assessment_input_current_binding
    ON hosting_controlplane.assessment_inputs
    (organization_id, tenant_id, kind, binding_digest, revision DESC);

CREATE TRIGGER assessment_input_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.assessment_inputs
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
REVOKE ALL ON hosting_controlplane.assessment_inputs FROM PUBLIC;
ALTER TABLE hosting_controlplane.assessment_inputs ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.assessment_inputs FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_input_tenant ON hosting_controlplane.assessment_inputs
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
-- Even an accidental inherited table grant cannot give a site worker a
-- control-plane evidence read or publication path through caller-set GUCs.
CREATE POLICY assessment_input_no_site_worker ON hosting_controlplane.assessment_inputs
    AS RESTRICTIVE FOR ALL
    USING (NOT hosting_controlplane.is_site_worker_role())
    WITH CHECK (NOT hosting_controlplane.is_site_worker_role());
