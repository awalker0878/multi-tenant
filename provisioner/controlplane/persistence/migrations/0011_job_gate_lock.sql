-- Read-only workflow Activities must serialize the job status projection
-- without receiving UPDATE privileges on jobs. FORCE RLS still applies to
-- this NOSUPERUSER/NOBYPASSRLS migration-owner SECURITY DEFINER function.
CREATE FUNCTION hosting_controlplane.lock_job_scope(
    p_organization_id text, p_tenant_id text, p_job_id text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
BEGIN
    IF current_setting('app.organization_id', true) IS DISTINCT FROM p_organization_id
       OR current_setting('app.tenant_id', true) IS DISTINCT FROM p_tenant_id THEN
        RAISE EXCEPTION 'Verified tenant context is required' USING ERRCODE = '42501';
    END IF;
    PERFORM 1 FROM hosting_controlplane.operation_jobs j
      WHERE j.organization_id = p_organization_id
        AND j.tenant_id = p_tenant_id AND j.job_id = p_job_id
      FOR SHARE;
    RETURN FOUND;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_job_scope(text, text, text)
    FROM PUBLIC;
