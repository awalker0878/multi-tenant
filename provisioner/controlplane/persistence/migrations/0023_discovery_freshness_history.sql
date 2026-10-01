-- Monitoring history is metadata, not collection or execution authority.
CREATE TABLE hosting_controlplane.discovery_freshness_checks (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    environment_id text NOT NULL,
    site_id text NOT NULL,
    security_domain_id text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    platform_family text NOT NULL,
    check_id text NOT NULL CHECK (check_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    sequence bigint NOT NULL CHECK (sequence > 0),
    report_json text NOT NULL CHECK (octet_length(report_json) BETWEEN 1 AND 8192
                                   AND jsonb_typeof(report_json::jsonb) = 'object'),
    report_digest text NOT NULL CHECK (report_digest ~ '^[0-9a-f]{64}$'),
    recorded_by text NOT NULL CHECK (length(recorded_by) BETWEEN 1 AND 512),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    previous_record_digest text CHECK (previous_record_digest ~ '^[0-9a-f]{64}$'),
    changes_json text NOT NULL CHECK (octet_length(changes_json) BETWEEN 2 AND 512
                                    AND jsonb_typeof(changes_json::jsonb) = 'array'),
    record_digest text NOT NULL CHECK (record_digest ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (organization_id, tenant_id, environment_id, sequence),
    UNIQUE (organization_id, tenant_id, environment_id, check_id),
    FOREIGN KEY (organization_id, tenant_id, environment_id, site_id,
                 security_domain_id, endpoint_id, native_scope_id, platform_family)
        REFERENCES hosting_controlplane.environment_registrations
        (organization_id, tenant_id, environment_id, site_id,
         security_domain_id, endpoint_id, native_scope_id, platform_family) ON DELETE RESTRICT,
    CHECK ((sequence = 1) = (previous_record_digest IS NULL)),
    CHECK ((report_json::jsonb ->> 'format') IS NOT DISTINCT FROM 'hosting-discovery-freshness/1'),
    CHECK ((report_json::jsonb ->> 'environmentId') IS NOT DISTINCT FROM environment_id),
    CHECK ((report_json::jsonb -> 'scope') IS NOT DISTINCT FROM jsonb_build_object(
        'organization_id',organization_id,'tenant_id',tenant_id,'site_id',site_id,
        'security_domain_id',security_domain_id,'endpoint_id',endpoint_id,
        'native_scope_id',native_scope_id,'platform_family',platform_family)),
    CHECK ((report_json::jsonb -> 'nativeVisibilityVerified') IS NOT DISTINCT FROM 'false'::jsonb),
    CHECK ((report_json::jsonb -> 'collectionRequested') IS NOT DISTINCT FROM 'false'::jsonb),
    CHECK ((report_json::jsonb -> 'executionAuthorized') IS NOT DISTINCT FROM 'false'::jsonb)
);
CREATE TRIGGER discovery_freshness_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.discovery_freshness_checks
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

CREATE FUNCTION hosting_controlplane.guard_discovery_freshness_sequence() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, hosting_controlplane AS $$
DECLARE previous hosting_controlplane.discovery_freshness_checks%ROWTYPE;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(jsonb_build_array(
        'discovery-freshness', NEW.organization_id, NEW.tenant_id, NEW.environment_id)::text, 0));
    SELECT * INTO previous FROM hosting_controlplane.discovery_freshness_checks
        WHERE organization_id=NEW.organization_id AND tenant_id=NEW.tenant_id
          AND environment_id=NEW.environment_id ORDER BY sequence DESC LIMIT 1;
    IF NEW.sequence <> COALESCE(previous.sequence, 0) + 1
        OR NEW.previous_record_digest IS DISTINCT FROM previous.record_digest
        OR NEW.recorded_at < previous.recorded_at THEN
        RAISE EXCEPTION 'Freshness history must append the exact predecessor' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.guard_discovery_freshness_sequence() FROM PUBLIC;
CREATE TRIGGER discovery_freshness_sequence BEFORE INSERT
    ON hosting_controlplane.discovery_freshness_checks
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_discovery_freshness_sequence();
REVOKE ALL ON hosting_controlplane.discovery_freshness_checks FROM PUBLIC;
ALTER TABLE hosting_controlplane.discovery_freshness_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.discovery_freshness_checks FORCE ROW LEVEL SECURITY;
CREATE POLICY discovery_freshness_tenant ON hosting_controlplane.discovery_freshness_checks
    USING (organization_id=current_setting('app.organization_id', true)
       AND tenant_id=current_setting('app.tenant_id', true))
    WITH CHECK (organization_id=current_setting('app.organization_id', true)
            AND tenant_id=current_setting('app.tenant_id', true));
CREATE POLICY discovery_freshness_no_site_worker ON hosting_controlplane.discovery_freshness_checks
    AS RESTRICTIVE FOR ALL
    USING (NOT hosting_controlplane.is_site_worker_role())
    WITH CHECK (NOT hosting_controlplane.is_site_worker_role());
