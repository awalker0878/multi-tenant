-- A worker subject persists across externally issued certificate renewals.
-- The enrollment row and its original fingerprint are immutable historical
-- identity facts. Current certificate authority resides in this version table.
ALTER TABLE hosting_controlplane.audit_events
    DROP CONSTRAINT audit_events_action_check;
ALTER TABLE hosting_controlplane.audit_events
    ADD CONSTRAINT audit_events_action_check CHECK (action IN
        ('RECORD_CREATE', 'RECORD_UPDATE', 'LEASE_ACQUIRE',
         'LEASE_RENEW', 'LEASE_RELEASE', 'WORKER_CERT_ENROLL',
         'WORKER_CERT_ROTATE', 'WORKER_CERT_REVOKE', 'WORKER_REVOKE'));

CREATE TABLE hosting_controlplane.worker_certificate_versions (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    worker_subject text NOT NULL,
    certificate_sha256 text NOT NULL CHECK (certificate_sha256 ~ '^[0-9a-f]{64}$'),
    enrolled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    PRIMARY KEY (organization_id, tenant_id, worker_subject, certificate_sha256),
    UNIQUE (certificate_sha256),
    FOREIGN KEY (organization_id, tenant_id, worker_subject)
        REFERENCES hosting_controlplane.worker_enrollments
        (organization_id, tenant_id, worker_subject) ON DELETE RESTRICT,
    CHECK (expires_at > enrolled_at)
);

INSERT INTO hosting_controlplane.worker_certificate_versions
    (organization_id, tenant_id, worker_subject, certificate_sha256,
     enrolled_at, expires_at, revoked_at)
SELECT organization_id, tenant_id, worker_subject, certificate_sha256,
       enrolled_at, expires_at, revoked_at
FROM hosting_controlplane.worker_enrollments;

CREATE TRIGGER worker_certificate_versions_change_guard BEFORE UPDATE
    ON hosting_controlplane.worker_certificate_versions FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.worker_enrollment_change_guard();

ALTER TABLE hosting_controlplane.worker_certificate_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.worker_certificate_versions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON hosting_controlplane.worker_certificate_versions
    USING (organization_id = current_setting('app.organization_id', true)
           AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
                AND tenant_id = current_setting('app.tenant_id', true));

CREATE OR REPLACE FUNCTION hosting_controlplane.lock_worker_scope(
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
    SELECT v.expires_at INTO current_expiry
    FROM hosting_controlplane.worker_enrollments e
    JOIN hosting_controlplane.worker_certificate_versions v
      ON v.organization_id = e.organization_id AND v.tenant_id = e.tenant_id
     AND v.worker_subject = e.worker_subject
    WHERE e.organization_id = p_organization_id AND e.tenant_id = p_tenant_id
      AND e.worker_subject = p_worker_subject AND e.site_id = p_site_id
      AND e.revoked_at IS NULL
      AND v.certificate_sha256 = p_certificate_sha256
      AND v.revoked_at IS NULL AND v.enrolled_at <= clock_timestamp()
      AND v.expires_at > clock_timestamp()
    FOR SHARE OF e, v;
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
