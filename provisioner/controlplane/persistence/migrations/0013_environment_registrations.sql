-- A human declaration is a selector for read-only review, never proof that a
-- platform exists, is reachable, is owned, or is qualified for a migration.
CREATE TABLE hosting_controlplane.environment_registrations (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    environment_id text NOT NULL CHECK
        (environment_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    display_name text NOT NULL CHECK
        (length(display_name) BETWEEN 1 AND 256
         AND display_name !~ '[[:cntrl:]]'),
    site_id text NOT NULL CHECK
        (site_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    security_domain_id text NOT NULL CHECK
        (security_domain_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    endpoint_id text NOT NULL CHECK
        (endpoint_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    native_scope_id text NOT NULL CHECK
        (length(native_scope_id) BETWEEN 1 AND 512
         AND btrim(native_scope_id) <> ''
         AND native_scope_id !~ '[[:cntrl:]]'),
    platform_family text NOT NULL CHECK
        (platform_family IN ('vmware', 'nutanix', 'openstack')),
    status text GENERATED ALWAYS AS ('DECLARED_UNVERIFIED'::text) STORED,
    registered_by text NOT NULL CHECK (length(registered_by) BETWEEN 1 AND 512),
    record_digest text NOT NULL CHECK (record_digest ~ '^[0-9a-f]{64}$'),
    registered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, environment_id),
    UNIQUE (organization_id, tenant_id, site_id, security_domain_id,
            endpoint_id, native_scope_id, platform_family)
);
CREATE INDEX environment_registrations_wsd_page
    ON hosting_controlplane.environment_registrations
    (organization_id, tenant_id, security_domain_id, environment_id);
CREATE TRIGGER environment_registrations_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.environment_registrations
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
ALTER TABLE hosting_controlplane.environment_registrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.environment_registrations FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_environment_registrations
    ON hosting_controlplane.environment_registrations
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
