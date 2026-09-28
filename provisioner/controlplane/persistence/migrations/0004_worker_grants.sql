-- Apply after 0003_authority.sql with a NOSUPERUSER, NOBYPASSRLS owner.
-- A worker gets no database login or grant-table DML. An enrollment writer
-- controls certificate and capability rows; only the trusted grant service
-- may insert grants. Credential references are not secret material.

CREATE DOMAIN hosting_controlplane.worker_operation_kind AS text CHECK (VALUE IN (
    'DISCOVER_READ', 'VM_CREATE', 'VM_POWER', 'DISK_ATTACH', 'NETWORK_ATTACH',
    'SNAPSHOT_CREATE', 'SNAPSHOT_EXPORT', 'SNAPSHOT_IMPORT', 'RESTORE_DATA',
    'SOURCE_FENCE', 'DESTINATION_ACTIVATE', 'DNS_CHANGE', 'IPAM_RESERVE'));

CREATE TABLE hosting_controlplane.worker_enrollments (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    worker_subject text NOT NULL,
    site_id text NOT NULL,
    certificate_sha256 text NOT NULL CHECK (certificate_sha256 ~ '^[0-9a-f]{64}$'),
    enrolled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    PRIMARY KEY (organization_id, tenant_id, worker_subject),
    UNIQUE (certificate_sha256),
    CHECK (length(worker_subject) > 0 AND length(site_id) > 0),
    CHECK (expires_at > enrolled_at)
);

CREATE TABLE hosting_controlplane.worker_capabilities (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    worker_subject text NOT NULL,
    site_id text NOT NULL,
    security_domain_id text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    platform_family text NOT NULL CHECK (platform_family IN
        ('vmware', 'nutanix', 'openstack')),
    operation_kind hosting_controlplane.worker_operation_kind NOT NULL,
    credential_ref text NOT NULL CHECK (length(credential_ref) BETWEEN 1 AND 512),
    revoked_at timestamptz,
    PRIMARY KEY (organization_id, tenant_id, worker_subject, site_id,
                 security_domain_id, endpoint_id, native_scope_id,
                 platform_family, operation_kind),
    FOREIGN KEY (organization_id, tenant_id, worker_subject)
        REFERENCES hosting_controlplane.worker_enrollments
        (organization_id, tenant_id, worker_subject) ON DELETE RESTRICT,
    CHECK (length(security_domain_id) > 0 AND length(endpoint_id) > 0
           AND length(native_scope_id) > 0)
);

CREATE TABLE hosting_controlplane.worker_grants (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    grant_id text NOT NULL,
    job_id text NOT NULL,
    plan_id text NOT NULL,
    plan_revision bigint NOT NULL CHECK (plan_revision > 0),
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[0-9a-f]{64}$'),
    approval_ids jsonb NOT NULL CHECK (jsonb_typeof(approval_ids) = 'array'),
    revocation_epoch bigint NOT NULL CHECK (revocation_epoch >= 0),
    worker_subject text NOT NULL,
    certificate_sha256 text NOT NULL CHECK (certificate_sha256 ~ '^[0-9a-f]{64}$'),
    step_id text NOT NULL,
    operation_id text NOT NULL,
    operation_kind hosting_controlplane.worker_operation_kind NOT NULL,
    site_id text NOT NULL,
    security_domain_id text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    platform_family text NOT NULL,
    lease_key text NOT NULL,
    lease_epoch bigint NOT NULL CHECK (lease_epoch > 0),
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    PRIMARY KEY (organization_id, tenant_id, grant_id),
    UNIQUE (organization_id, tenant_id, job_id, step_id, operation_id, lease_epoch),
    FOREIGN KEY (organization_id, tenant_id, job_id)
        REFERENCES hosting_controlplane.operation_jobs
        (organization_id, tenant_id, job_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, tenant_id, worker_subject)
        REFERENCES hosting_controlplane.worker_enrollments
        (organization_id, tenant_id, worker_subject) ON DELETE RESTRICT,
    CHECK (expires_at > issued_at AND expires_at <= issued_at + interval '5 minutes'),
    CHECK (platform_family IN ('vmware', 'nutanix', 'openstack')),
    CHECK (length(step_id) > 0 AND length(operation_id) > 0
           AND length(lease_key) > 0)
);

CREATE FUNCTION hosting_controlplane.worker_enrollment_change_guard()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (to_jsonb(NEW) - 'revoked_at') IS DISTINCT FROM
       (to_jsonb(OLD) - 'revoked_at')
       OR OLD.revoked_at IS NOT NULL OR NEW.revoked_at IS NULL THEN
        RAISE EXCEPTION 'Worker identity and capability are immutable; only revocation is allowed';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER enrollment_change_guard BEFORE UPDATE
    ON hosting_controlplane.worker_enrollments FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.worker_enrollment_change_guard();
CREATE TRIGGER capability_change_guard BEFORE UPDATE
    ON hosting_controlplane.worker_capabilities FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.worker_enrollment_change_guard();
CREATE TRIGGER grants_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.worker_grants FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['worker_enrollments', 'worker_capabilities',
                                       'worker_grants'] LOOP
        EXECUTE format('ALTER TABLE hosting_controlplane.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE hosting_controlplane.%I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format(
            'CREATE POLICY tenant_scope ON hosting_controlplane.%I '
            || 'USING (organization_id = current_setting(''app.organization_id'', true) '
            || 'AND tenant_id = current_setting(''app.tenant_id'', true)) '
            || 'WITH CHECK (organization_id = current_setting(''app.organization_id'', true) '
            || 'AND tenant_id = current_setting(''app.tenant_id'', true))',
            table_name);
    END LOOP;
END $$;

-- SELECT FOR SHARE needs UPDATE privilege. The grant role receives only this
-- narrow lock function, never UPDATE on enrollment or capability records.
CREATE FUNCTION hosting_controlplane.lock_worker_scope(
    p_organization_id text, p_tenant_id text, p_worker_subject text,
    p_certificate_sha256 text, p_site_id text, p_security_domain_id text,
    p_endpoint_id text, p_native_scope_id text, p_platform_family text,
    p_operation_kind text)
RETURNS TABLE (credential_ref text, enrollment_expires_at timestamptz)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
DECLARE current_expiry timestamptz;
BEGIN
    IF current_setting('app.organization_id', true) IS DISTINCT FROM p_organization_id
       OR current_setting('app.tenant_id', true) IS DISTINCT FROM p_tenant_id THEN
        RAISE EXCEPTION 'Verified tenant context is required' USING ERRCODE = '42501';
    END IF;
    SELECT e.expires_at INTO current_expiry
    FROM hosting_controlplane.worker_enrollments e
    WHERE e.organization_id = p_organization_id AND e.tenant_id = p_tenant_id
      AND e.worker_subject = p_worker_subject AND e.site_id = p_site_id
      AND e.certificate_sha256 = p_certificate_sha256
      AND e.revoked_at IS NULL AND e.enrolled_at <= clock_timestamp()
      AND e.expires_at > clock_timestamp()
    FOR SHARE;
    IF NOT FOUND THEN RETURN; END IF;
    RETURN QUERY SELECT c.credential_ref, current_expiry
    FROM hosting_controlplane.worker_capabilities c
    WHERE c.organization_id = p_organization_id AND c.tenant_id = p_tenant_id
      AND c.worker_subject = p_worker_subject AND c.site_id = p_site_id
      AND c.security_domain_id = p_security_domain_id
      AND c.endpoint_id = p_endpoint_id AND c.native_scope_id = p_native_scope_id
      AND c.platform_family = p_platform_family
      AND c.operation_kind = p_operation_kind
      AND c.revoked_at IS NULL
    FOR SHARE;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_worker_scope(
    text, text, text, text, text, text, text, text, text, text) FROM PUBLIC;
