-- A site credential listener must lock the current operation lease and owner
-- without receiving UPDATE on the owner, job, or immutable lease table.
-- The migration owner is NOSUPERUSER/NOBYPASSRLS and FORCE RLS still applies.
CREATE FUNCTION hosting_controlplane.lock_native_worker_scope(
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
        AND l.lease_key = p_lease_key FOR SHARE;
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
REVOKE ALL ON FUNCTION hosting_controlplane.lock_native_worker_scope(
    text, text, text) FROM PUBLIC;
