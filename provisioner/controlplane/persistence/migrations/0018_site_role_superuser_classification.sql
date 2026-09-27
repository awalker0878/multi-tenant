-- Correct superuser group membership classification on upgraded installations.
-- PostgreSQL treats a superuser as implicitly having every role for
-- pg_has_role(..., 'member'). Some isolated integration suites use SET ROLE
-- from a superuser session; that session must not be mistaken for a site
-- credential. Production site logins are never superusers. The immutable
-- binding and hosting_site_* name still classify removed-group logins.
CREATE OR REPLACE FUNCTION hosting_controlplane.is_site_worker_role()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
    SELECT left(session_user::text, 13) = 'hosting_site_'
        OR EXISTS (
            SELECT 1 FROM hosting_controlplane.site_worker_role_bindings b
            WHERE b.role_name = session_user::name)
        OR (NOT EXISTS (
                SELECT 1 FROM pg_catalog.pg_roles r
                WHERE r.rolname = session_user AND r.rolsuper)
            AND pg_catalog.pg_has_role(
                session_user, 'hosting_site_worker_roles', 'member'));
$$;

-- Existing lock helpers must call the corrected session classifier rather
-- than querying pg_has_role separately. Preserve their EXECUTE ACLs.
CREATE OR REPLACE FUNCTION hosting_controlplane.lock_job_scope(
    p_organization_id text, p_tenant_id text, p_job_id text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
BEGIN
    IF current_setting('app.organization_id', true) IS DISTINCT FROM p_organization_id
       OR current_setting('app.tenant_id', true) IS DISTINCT FROM p_tenant_id THEN
        RAISE EXCEPTION 'Verified tenant context is required' USING ERRCODE = '42501';
    END IF;
    IF hosting_controlplane.is_site_worker_role()
       AND NOT hosting_controlplane.site_worker_job_visible(
           p_organization_id, p_tenant_id, p_job_id) THEN
        RAISE EXCEPTION 'Site worker role cannot lock this job' USING ERRCODE = '42501';
    END IF;
    PERFORM 1 FROM hosting_controlplane.operation_jobs j
      WHERE j.organization_id = p_organization_id
        AND j.tenant_id = p_tenant_id AND j.job_id = p_job_id
      FOR SHARE;
    RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION hosting_controlplane.lock_authority_scope(
    p_organization_id text, p_tenant_id text, p_plan_id text)
RETURNS TABLE (plan_revision bigint, plan_digest text, revocation_epoch bigint)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
DECLARE
    workload_id text;
    current_revision bigint;
    current_digest text;
    current_epoch bigint;
BEGIN
    IF current_setting('app.organization_id', true) IS DISTINCT FROM p_organization_id
       OR current_setting('app.tenant_id', true) IS DISTINCT FROM p_tenant_id THEN
        RAISE EXCEPTION 'Verified tenant context is required' USING ERRCODE = '42501';
    END IF;
    IF hosting_controlplane.is_site_worker_role()
       AND NOT EXISTS (
           SELECT 1 FROM hosting_controlplane.worker_grants g
           WHERE g.organization_id = p_organization_id
             AND g.tenant_id = p_tenant_id AND g.plan_id = p_plan_id
             AND g.issued_at <= now() AND g.expires_at > now()
             AND hosting_controlplane.site_worker_role_matches(
                 g.organization_id, g.tenant_id, g.site_id)) THEN
        RAISE EXCEPTION 'Site worker role cannot lock this plan' USING ERRCODE = '42501';
    END IF;
    SELECT s.plan_revision, s.plan_digest, s.revocation_epoch
    INTO current_revision, current_digest, current_epoch
    FROM hosting_controlplane.plan_authority_state s
    WHERE s.organization_id = p_organization_id AND s.tenant_id = p_tenant_id
      AND s.plan_id = p_plan_id FOR SHARE;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT e.record_json->'spec'->>'workloadId' INTO workload_id
    FROM hosting_controlplane.enterprise_records e
    WHERE e.organization_id = p_organization_id AND e.tenant_id = p_tenant_id
      AND e.record_kind = 'MigrationPlan' AND e.record_id = p_plan_id;
    IF workload_id IS NULL THEN RETURN; END IF;
    PERFORM 1 FROM hosting_controlplane.enterprise_records w
    WHERE w.organization_id = p_organization_id AND w.tenant_id = p_tenant_id
      AND w.record_kind = 'Workload' AND w.record_id = workload_id FOR SHARE;
    IF NOT FOUND THEN RETURN; END IF;
    RETURN QUERY SELECT current_revision, current_digest, current_epoch;
END;
$$;

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
    IF hosting_controlplane.is_site_worker_role()
       AND (p_operation_kind IS DISTINCT FROM 'DISCOVER_READ'
            OR NOT hosting_controlplane.site_worker_role_matches(
                p_organization_id, p_tenant_id, p_site_id)) THEN
        RAISE EXCEPTION 'Site worker role cannot lock this read scope' USING ERRCODE = '42501';
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

CREATE OR REPLACE FUNCTION hosting_controlplane.lock_native_worker_scope(
    p_organization_id text, p_tenant_id text, p_lease_key text)
RETURNS TABLE (
    job_id text, operation_id text, platform_family text, endpoint_id text,
    native_scope_id text, resource_kind text, native_id text, site_id text,
    security_domain_id text, worker_id text, owner_epoch bigint,
    expires_at timestamptz, owner_organization_id text, owner_tenant_id text,
    owner_security_domain_id text, owner_worker_id text,
    owner_lease_epoch bigint, owner_lease_expires_at timestamptz)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
DECLARE lease_row hosting_controlplane.native_operation_leases%ROWTYPE;
BEGIN
    IF current_setting('app.organization_id', true) IS DISTINCT FROM p_organization_id
       OR current_setting('app.tenant_id', true) IS DISTINCT FROM p_tenant_id THEN
        RAISE EXCEPTION 'Verified tenant context is required' USING ERRCODE = '42501';
    END IF;
    SELECT l.* INTO lease_row FROM hosting_controlplane.native_operation_leases l
      WHERE l.organization_id = p_organization_id AND l.tenant_id = p_tenant_id
        AND l.lease_key = p_lease_key
        AND (NOT hosting_controlplane.is_site_worker_role()
             OR hosting_controlplane.site_worker_role_matches(
                 l.organization_id, l.tenant_id, l.site_id))
      FOR SHARE;
    IF NOT FOUND THEN RETURN; END IF;
    RETURN QUERY SELECT lease_row.job_id, lease_row.operation_id,
        lease_row.platform_family, lease_row.endpoint_id,
        lease_row.native_scope_id, lease_row.resource_kind,
        lease_row.native_id, lease_row.site_id, lease_row.security_domain_id,
        lease_row.worker_id, lease_row.owner_epoch, lease_row.expires_at,
        o.organization_id, o.tenant_id, o.security_domain_id, o.worker_id,
        o.lease_epoch, o.lease_expires_at
      FROM hosting_controlplane.native_ownership o
      WHERE o.platform_family = lease_row.platform_family
        AND o.endpoint_id = lease_row.endpoint_id
        AND o.native_scope_id = lease_row.native_scope_id
        AND o.resource_kind = lease_row.resource_kind
        AND o.native_id = lease_row.native_id FOR SHARE;
END;
$$;

-- CREATE OR REPLACE preserves existing EXECUTE ACLs; keep PUBLIC excluded.
REVOKE ALL ON FUNCTION hosting_controlplane.lock_job_scope(text, text, text)
    FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_authority_scope(text, text, text)
    FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_worker_scope(
    text, text, text, text, text, text, text, text, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_native_worker_scope(
    text, text, text) FROM PUBLIC;
