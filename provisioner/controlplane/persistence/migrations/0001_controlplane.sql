-- Apply with the packaged migration runner and a dedicated migration role.
-- The runtime role must be separate, non-superuser and NOBYPASSRLS.
CREATE SCHEMA hosting_controlplane;
REVOKE ALL ON SCHEMA hosting_controlplane FROM PUBLIC;

CREATE TABLE hosting_controlplane.schema_migrations (
    version text PRIMARY KEY,
    script_digest text NOT NULL CHECK (script_digest ~ '^[0-9a-f]{64}$'),
    applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE hosting_controlplane.enterprise_records (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    record_kind text NOT NULL CHECK (record_kind IN
        ('Workload', 'ApplicationGroup', 'ObservationSnapshot',
         'MigrationPlan', 'TransferManifest', 'ActivityResult')),
    record_id text NOT NULL,
    revision bigint NOT NULL CHECK (revision > 0),
    record_json jsonb NOT NULL,
    record_digest text NOT NULL CHECK (record_digest ~ '^[0-9a-f]{64}$'),
    security_domain_id text GENERATED ALWAYS AS
        (CASE WHEN record_kind = 'Workload'
              THEN record_json->'metadata'->>'wsdId' ELSE NULL END) STORED,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, record_kind, record_id),
    CHECK (jsonb_typeof(record_json) = 'object'),
    CHECK (jsonb_typeof(record_json->'metadata') = 'object'),
    CHECK ((record_json->>'kind' = record_kind) IS TRUE),
    CHECK ((record_json->'metadata'->>'organizationId' = organization_id) IS TRUE),
    CHECK ((record_json->'metadata'->>'tenantId' = tenant_id) IS TRUE),
    CHECK ((record_id = CASE record_kind
        WHEN 'Workload' THEN record_json->'metadata'->>'workloadId'
        WHEN 'ApplicationGroup' THEN record_json->'metadata'->>'applicationGroupId'
        WHEN 'ObservationSnapshot' THEN record_json->'metadata'->>'snapshotId'
        WHEN 'MigrationPlan' THEN record_json->'metadata'->>'planId'
        WHEN 'TransferManifest' THEN record_json->'metadata'->>'transferId'
        WHEN 'ActivityResult' THEN record_json->'metadata'->>'activityId'
    END) IS TRUE),
    CHECK ((revision = COALESCE((record_json->'metadata'->>'revision')::bigint, 1)) IS TRUE)
);
CREATE INDEX enterprise_records_kind_page
    ON hosting_controlplane.enterprise_records
    (organization_id, tenant_id, record_kind, record_id);
CREATE INDEX enterprise_workloads_wsd_page
    ON hosting_controlplane.enterprise_records
    (organization_id, tenant_id, security_domain_id, record_id)
    WHERE record_kind = 'Workload';

CREATE TABLE hosting_controlplane.enterprise_record_history (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    record_kind text NOT NULL,
    record_id text NOT NULL,
    revision bigint NOT NULL CHECK (revision > 0),
    record_json jsonb NOT NULL,
    record_digest text NOT NULL CHECK (record_digest ~ '^[0-9a-f]{64}$'),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, record_kind, record_id, revision),
    FOREIGN KEY (organization_id, tenant_id, record_kind, record_id)
        REFERENCES hosting_controlplane.enterprise_records
        (organization_id, tenant_id, record_kind, record_id) ON DELETE RESTRICT,
    CHECK ((record_json->>'kind' = record_kind) IS TRUE),
    CHECK ((record_json->'metadata'->>'organizationId' = organization_id) IS TRUE),
    CHECK ((record_json->'metadata'->>'tenantId' = tenant_id) IS TRUE)
);

CREATE TABLE hosting_controlplane.audit_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    actor_id text NOT NULL CHECK (length(actor_id) > 0),
    correlation_id text NOT NULL CHECK (length(correlation_id) > 0),
    action text NOT NULL CHECK (action IN
        ('RECORD_CREATE', 'RECORD_UPDATE', 'LEASE_ACQUIRE',
         'LEASE_RENEW', 'LEASE_RELEASE')),
    record_kind text NOT NULL,
    record_id text NOT NULL,
    revision bigint NOT NULL CHECK (revision > 0),
    record_digest text NOT NULL CHECK (record_digest ~ '^[0-9a-f]{64}$'),
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX audit_events_tenant_order
    ON hosting_controlplane.audit_events
    (organization_id, tenant_id, event_id);

CREATE TABLE hosting_controlplane.native_ownership (
    platform_family text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    resource_kind text NOT NULL,
    native_id text NOT NULL,
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    security_domain_id text NOT NULL,
    workload_id text NOT NULL,
    workload_kind text NOT NULL DEFAULT 'Workload' CHECK (workload_kind = 'Workload'),
    worker_id text,
    lease_epoch bigint NOT NULL DEFAULT 1 CHECK (lease_epoch > 0),
    lease_expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (platform_family, endpoint_id, native_scope_id,
                 resource_kind, native_id),
    FOREIGN KEY (organization_id, tenant_id, workload_kind, workload_id)
        REFERENCES hosting_controlplane.enterprise_records
        (organization_id, tenant_id, record_kind, record_id)
        DEFERRABLE INITIALLY IMMEDIATE,
    CHECK ((worker_id IS NULL) = (lease_expires_at IS NULL)),
    CHECK (platform_family IN ('vmware', 'nutanix', 'openstack')),
    CHECK (resource_kind IN ('vm', 'disk', 'nic', 'volume', 'dataset', 'network'))
);

CREATE FUNCTION hosting_controlplane.prevent_append_only_changes()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Append-only control-plane history cannot be changed';
END;
$$;
CREATE FUNCTION hosting_controlplane.check_native_owner_wsd()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE accepted_wsd text;
BEGIN
    SELECT security_domain_id INTO accepted_wsd
    FROM hosting_controlplane.enterprise_records
    WHERE organization_id = NEW.organization_id
      AND tenant_id = NEW.tenant_id
      AND record_kind = 'Workload'
      AND record_id = NEW.workload_id
    FOR SHARE;
    IF accepted_wsd IS NULL OR accepted_wsd != NEW.security_domain_id THEN
        RAISE EXCEPTION 'Native owner must use accepted workload security domain';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER native_owner_wsd_guard
    BEFORE INSERT OR UPDATE OF security_domain_id, workload_id
    ON hosting_controlplane.native_ownership
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.check_native_owner_wsd();
CREATE TRIGGER history_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.enterprise_record_history
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER audit_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.audit_events
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

ALTER TABLE hosting_controlplane.enterprise_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.enterprise_records FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.enterprise_record_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.enterprise_record_history FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.audit_events FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.native_ownership ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.native_ownership FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_records ON hosting_controlplane.enterprise_records
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY tenant_history ON hosting_controlplane.enterprise_record_history
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY tenant_audit ON hosting_controlplane.audit_events
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY tenant_ownership ON hosting_controlplane.native_ownership
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
