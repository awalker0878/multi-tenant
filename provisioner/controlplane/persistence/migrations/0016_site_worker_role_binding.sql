-- Site SQL credentials are individually bound to one organization, tenant,
-- and site. A database administrator must first create the NOLOGIN,
-- NOSUPERUSER, NOBYPASSRLS role hosting_site_worker_roles, and grant membership
-- only to dedicated site LOGIN roles. The migration owner must itself be
-- NOSUPERUSER/NOBYPASSRLS and must not be a member of that group.
--
-- The mapping is written only by the migration owner after site credential
-- enrollment. No site login, API role, or grant writer receives table DML.
-- session_user survives SET ROLE and SECURITY DEFINER calls; app.* GUCs do not
-- authenticate this binding. A hosting_site_* login without a binding is also
-- classified as a site worker and denied, even if group membership is missing.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles
        WHERE rolname = 'hosting_site_worker_roles' AND NOT rolcanlogin
          AND NOT rolsuper AND NOT rolbypassrls
    ) THEN
        RAISE EXCEPTION 'Precreate the restricted hosting_site_worker_roles group';
    END IF;
    IF pg_catalog.pg_has_role(session_user, 'hosting_site_worker_roles', 'member') THEN
        RAISE EXCEPTION 'Migration owner cannot be a site worker';
    END IF;
END $$;

CREATE TABLE hosting_controlplane.site_worker_role_bindings (
    role_name name PRIMARY KEY,
    organization_id text NOT NULL CHECK (length(organization_id) > 0),
    tenant_id text NOT NULL CHECK (length(tenant_id) > 0),
    site_id text NOT NULL CHECK (length(site_id) > 0),
    bound_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
REVOKE ALL ON hosting_controlplane.site_worker_role_bindings FROM PUBLIC;

CREATE FUNCTION hosting_controlplane.guard_site_worker_role_binding()
RETURNS trigger LANGUAGE plpgsql
SET search_path = pg_catalog, hosting_controlplane AS $$
BEGIN
    IF TG_OP != 'INSERT' THEN
        RAISE EXCEPTION 'Site worker SQL role bindings are immutable';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles r
        WHERE r.rolname = NEW.role_name AND r.rolcanlogin
          AND NOT r.rolsuper AND NOT r.rolbypassrls
          AND pg_catalog.pg_has_role(r.rolname, 'hosting_site_worker_roles', 'member')
    ) THEN
        RAISE EXCEPTION 'Site worker login must be a restricted group member';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER site_worker_role_binding_guard
    BEFORE INSERT OR UPDATE OR DELETE
    ON hosting_controlplane.site_worker_role_bindings
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_site_worker_role_binding();

CREATE FUNCTION hosting_controlplane.is_site_worker_role()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
    SELECT left(session_user::text, 13) = 'hosting_site_'
        OR pg_catalog.pg_has_role(session_user, 'hosting_site_worker_roles', 'member')
        OR EXISTS (
            SELECT 1 FROM hosting_controlplane.site_worker_role_bindings b
            WHERE b.role_name = session_user::name);
$$;

CREATE FUNCTION hosting_controlplane.site_worker_role_matches(
    p_organization_id text, p_tenant_id text, p_site_id text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
    SELECT pg_catalog.pg_has_role(session_user, 'hosting_site_worker_roles', 'member')
       AND EXISTS (
           SELECT 1 FROM hosting_controlplane.site_worker_role_bindings b
           WHERE b.role_name = session_user::name
             AND b.organization_id = p_organization_id
             AND b.tenant_id = p_tenant_id AND b.site_id = p_site_id);
$$;

-- Keep the admitted plan-to-workload binding as a separate, owner-only fact.
-- A current plan record can advance after admission, and the historical plan
-- may not exist for records written before history enforcement. The job row
-- itself contains no workload ID; deriving this on every enterprise_records
-- SELECT would make that table's own RLS policy recursive.
CREATE TABLE hosting_controlplane.job_workload_bindings (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    job_id text NOT NULL,
    workload_id text NOT NULL CHECK (length(workload_id) > 0),
    workload_revision bigint NOT NULL CHECK (workload_revision > 0),
    PRIMARY KEY (organization_id, tenant_id, job_id),
    FOREIGN KEY (organization_id, tenant_id, job_id)
        REFERENCES hosting_controlplane.operation_jobs
        (organization_id, tenant_id, job_id) ON DELETE RESTRICT
);
REVOKE ALL ON hosting_controlplane.job_workload_bindings FROM PUBLIC;
CREATE TRIGGER job_workload_binding_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.job_workload_bindings
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

CREATE FUNCTION hosting_controlplane.bind_job_workload()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
DECLARE
    selected_workload text;
    selected_revision bigint;
BEGIN
    SELECT plan_snapshot.record_json->'spec'->>'workloadId',
           (plan_snapshot.record_json->'spec'->>'workloadRevision')::bigint
      INTO selected_workload, selected_revision
      FROM (
          SELECT h.record_json, 0 AS priority
          FROM hosting_controlplane.enterprise_record_history h
          WHERE h.organization_id = NEW.organization_id
            AND h.tenant_id = NEW.tenant_id
            AND h.record_kind = 'MigrationPlan' AND h.record_id = NEW.plan_id
            AND h.revision = NEW.plan_revision
            AND h.record_json->'metadata'->>'planDigest' = NEW.plan_digest
          UNION ALL
          SELECT p.record_json, 1 AS priority
          FROM hosting_controlplane.enterprise_records p
          WHERE p.organization_id = NEW.organization_id
            AND p.tenant_id = NEW.tenant_id
            AND p.record_kind = 'MigrationPlan' AND p.record_id = NEW.plan_id
            AND p.revision = NEW.plan_revision
            AND p.record_json->'metadata'->>'planDigest' = NEW.plan_digest
      ) plan_snapshot ORDER BY priority LIMIT 1;
    IF selected_workload IS NULL OR selected_revision IS NULL
       OR selected_revision < 1 THEN
        RAISE EXCEPTION 'Admitted job lacks an exact plan/workload revision';
    END IF;
    INSERT INTO hosting_controlplane.job_workload_bindings
        (organization_id, tenant_id, job_id, workload_id, workload_revision)
    VALUES (NEW.organization_id, NEW.tenant_id, NEW.job_id,
            selected_workload, selected_revision);
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.bind_job_workload() FROM PUBLIC;

-- The lock covers the brief owner-only backfill while FORCE RLS is relaxed.
-- These changes are transactional: no concurrent runtime can observe them.
LOCK TABLE hosting_controlplane.operation_jobs,
    hosting_controlplane.enterprise_records,
    hosting_controlplane.enterprise_record_history IN ACCESS EXCLUSIVE MODE;
ALTER TABLE hosting_controlplane.operation_jobs NO FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.enterprise_records NO FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.enterprise_record_history NO FORCE ROW LEVEL SECURITY;
INSERT INTO hosting_controlplane.job_workload_bindings
    (organization_id, tenant_id, job_id, workload_id, workload_revision)
SELECT j.organization_id, j.tenant_id, j.job_id,
       snapshot.record_json->'spec'->>'workloadId',
       (snapshot.record_json->'spec'->>'workloadRevision')::bigint
FROM hosting_controlplane.operation_jobs j
CROSS JOIN LATERAL (
    SELECT record_json, 0 AS priority
    FROM hosting_controlplane.enterprise_record_history h
    WHERE h.organization_id = j.organization_id
      AND h.tenant_id = j.tenant_id
      AND h.record_kind = 'MigrationPlan' AND h.record_id = j.plan_id
      AND h.revision = j.plan_revision
      AND h.record_json->'metadata'->>'planDigest' = j.plan_digest
    UNION ALL
    SELECT record_json, 1 AS priority
    FROM hosting_controlplane.enterprise_records p
    WHERE p.organization_id = j.organization_id
      AND p.tenant_id = j.tenant_id
      AND p.record_kind = 'MigrationPlan' AND p.record_id = j.plan_id
      AND p.revision = j.plan_revision
      AND p.record_json->'metadata'->>'planDigest' = j.plan_digest
    ORDER BY priority LIMIT 1
) snapshot;
DO $$
BEGIN
    IF (SELECT count(*) FROM hosting_controlplane.job_workload_bindings)
       != (SELECT count(*) FROM hosting_controlplane.operation_jobs) THEN
        RAISE EXCEPTION 'Cannot bind every admitted job to a plan/workload revision';
    END IF;
END $$;
ALTER TABLE hosting_controlplane.enterprise_record_history FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.enterprise_records FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.operation_jobs FORCE ROW LEVEL SECURITY;
CREATE TRIGGER operation_job_binds_workload AFTER INSERT
    ON hosting_controlplane.operation_jobs
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.bind_job_workload();

-- This function is used by the operation_jobs policy. It never queries jobs,
-- so the RLS dependency is acyclic: jobs -> grants -> immutable role binding.
CREATE FUNCTION hosting_controlplane.site_worker_job_visible(
    p_organization_id text, p_tenant_id text, p_job_id text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
    SELECT hosting_controlplane.is_site_worker_role() AND EXISTS (
        SELECT 1 FROM hosting_controlplane.worker_grants g
        JOIN hosting_controlplane.plan_authority_state s
          ON s.organization_id = g.organization_id
         AND s.tenant_id = g.tenant_id AND s.plan_id = g.plan_id
         AND s.plan_revision = g.plan_revision
         AND s.plan_digest = g.plan_digest
         AND s.revocation_epoch = g.revocation_epoch
        WHERE g.organization_id = p_organization_id
          AND g.tenant_id = p_tenant_id AND g.job_id = p_job_id
          AND g.issued_at <= statement_timestamp()
          AND g.expires_at > statement_timestamp()
          AND hosting_controlplane.site_worker_role_matches(
              g.organization_id, g.tenant_id, g.site_id));
$$;

-- A plan is visible only while its exact admitted revision/digest is active.
-- The jobs policy already requires a live grant for this login's site.
CREATE FUNCTION hosting_controlplane.site_worker_plan_visible(
    p_organization_id text, p_tenant_id text, p_plan_id text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
    SELECT hosting_controlplane.is_site_worker_role() AND EXISTS (
        SELECT 1 FROM hosting_controlplane.operation_jobs j
        WHERE j.organization_id = p_organization_id
          AND j.tenant_id = p_tenant_id AND j.plan_id = p_plan_id
          AND j.status IN ('STARTED', 'RUNNING')
          AND EXISTS (
              SELECT 1 FROM hosting_controlplane.enterprise_records p
              WHERE p.organization_id = j.organization_id
                AND p.tenant_id = j.tenant_id
                AND p.record_kind = 'MigrationPlan'
                AND p.record_id = j.plan_id
                AND p.revision = j.plan_revision
                AND p.record_json->'metadata'->>'planDigest' = j.plan_digest));
$$;

-- This helper never queries enterprise_records: its policy can safely call it.
CREATE FUNCTION hosting_controlplane.site_worker_record_visible(
    p_organization_id text, p_tenant_id text, p_record_kind text,
    p_record_id text, p_revision bigint, p_record_json jsonb)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
    SELECT hosting_controlplane.is_site_worker_role() AND
      CASE p_record_kind
        WHEN 'MigrationPlan' THEN EXISTS (
            SELECT 1 FROM hosting_controlplane.operation_jobs j
            WHERE j.organization_id = p_organization_id
              AND j.tenant_id = p_tenant_id
              AND j.plan_id = p_record_id AND j.plan_revision = p_revision
              AND j.plan_digest = p_record_json->'metadata'->>'planDigest'
              AND j.status IN ('STARTED', 'RUNNING'))
        WHEN 'Workload' THEN EXISTS (
            SELECT 1 FROM hosting_controlplane.operation_jobs j
            JOIN hosting_controlplane.job_workload_bindings b
              ON b.organization_id = j.organization_id
             AND b.tenant_id = j.tenant_id AND b.job_id = j.job_id
            WHERE j.organization_id = p_organization_id
              AND j.tenant_id = p_tenant_id
              AND j.status IN ('STARTED', 'RUNNING')
              AND b.workload_id = p_record_id
              AND b.workload_revision = p_revision)
        ELSE false END;
$$;

CREATE FUNCTION hosting_controlplane.site_worker_approval_visible(
    p_organization_id text, p_tenant_id text, p_plan_id text,
    p_plan_revision bigint, p_plan_digest text, p_revocation_epoch bigint)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
    SELECT hosting_controlplane.is_site_worker_role()
       AND hosting_controlplane.site_worker_plan_visible(
        p_organization_id, p_tenant_id, p_plan_id)
       AND EXISTS (
           SELECT 1 FROM hosting_controlplane.operation_jobs j
           WHERE j.organization_id = p_organization_id
             AND j.tenant_id = p_tenant_id AND j.plan_id = p_plan_id
             AND j.plan_revision = p_plan_revision
             AND j.plan_digest = p_plan_digest
             AND j.revocation_epoch = p_revocation_epoch
             AND j.status IN ('STARTED', 'RUNNING'));
$$;

CREATE FUNCTION hosting_controlplane.site_worker_audit_visible(
    p_organization_id text, p_tenant_id text, p_record_kind text,
    p_record_id text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
    SELECT hosting_controlplane.is_site_worker_role()
       AND p_record_kind = 'MigrationPlan'
       AND hosting_controlplane.site_worker_plan_visible(
           p_organization_id, p_tenant_id, p_record_id);
$$;

CREATE FUNCTION hosting_controlplane.site_worker_containment_visible(
    p_organization_id text, p_tenant_id text, p_platform_family text,
    p_endpoint_id text, p_native_scope_id text, p_resource_kind text,
    p_native_id text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
    SELECT hosting_controlplane.is_site_worker_role() AND EXISTS (
        SELECT 1 FROM hosting_controlplane.native_operation_leases l
        JOIN hosting_controlplane.worker_grants g
          ON g.organization_id = l.organization_id
         AND g.tenant_id = l.tenant_id AND g.job_id = l.job_id
         AND g.lease_key = l.lease_key AND g.site_id = l.site_id
        JOIN hosting_controlplane.operation_jobs j
          ON j.organization_id = l.organization_id
         AND j.tenant_id = l.tenant_id AND j.job_id = l.job_id
        WHERE l.organization_id = p_organization_id
          AND l.tenant_id = p_tenant_id
          AND l.platform_family = p_platform_family
          AND l.endpoint_id = p_endpoint_id
          AND l.native_scope_id = p_native_scope_id
          AND l.resource_kind = p_resource_kind AND l.native_id = p_native_id
          AND g.issued_at <= statement_timestamp()
          AND g.expires_at > statement_timestamp()
          AND j.status IN ('STARTED', 'RUNNING')
          AND hosting_controlplane.site_worker_role_matches(
              g.organization_id, g.tenant_id, g.site_id));
$$;

-- The existing permissive tenant policies still apply. These restrictive
-- SELECT policies additionally apply under SECURITY DEFINER because they
-- classify session_user rather than current_user or an application GUC.
CREATE POLICY site_worker_grants_read
    ON hosting_controlplane.worker_grants AS RESTRICTIVE FOR SELECT TO PUBLIC
    USING (CASE WHEN hosting_controlplane.is_site_worker_role()
        THEN hosting_controlplane.site_worker_role_matches(
            organization_id, tenant_id, site_id)
             AND issued_at <= statement_timestamp()
             AND expires_at > statement_timestamp()
        ELSE true END);

CREATE POLICY site_worker_jobs_read
    ON hosting_controlplane.operation_jobs AS RESTRICTIVE FOR SELECT TO PUBLIC
    USING (CASE WHEN hosting_controlplane.is_site_worker_role()
        THEN status IN ('STARTED', 'RUNNING')
             AND hosting_controlplane.site_worker_job_visible(
                 organization_id, tenant_id, job_id)
        ELSE true END);

CREATE POLICY site_worker_records_read
    ON hosting_controlplane.enterprise_records AS RESTRICTIVE FOR SELECT TO PUBLIC
    USING (CASE WHEN hosting_controlplane.is_site_worker_role()
        THEN hosting_controlplane.site_worker_record_visible(
            organization_id, tenant_id, record_kind, record_id,
            revision, record_json)
        ELSE true END);

CREATE POLICY site_worker_approvals_read
    ON hosting_controlplane.plan_approvals AS RESTRICTIVE FOR SELECT TO PUBLIC
    USING (CASE WHEN hosting_controlplane.is_site_worker_role()
        THEN hosting_controlplane.site_worker_approval_visible(
            organization_id, tenant_id, plan_id, plan_revision,
            plan_digest, revocation_epoch)
        ELSE true END);

CREATE POLICY site_worker_audit_read
    ON hosting_controlplane.audit_events AS RESTRICTIVE FOR SELECT TO PUBLIC
    USING (CASE WHEN hosting_controlplane.is_site_worker_role()
        THEN hosting_controlplane.site_worker_audit_visible(
            organization_id, tenant_id, record_kind, record_id)
        ELSE true END);

CREATE POLICY site_worker_containment_read
    ON hosting_controlplane.native_containment_holds
    AS RESTRICTIVE FOR SELECT TO PUBLIC
    USING (CASE WHEN hosting_controlplane.is_site_worker_role()
        THEN hosting_controlplane.site_worker_containment_visible(
            organization_id, tenant_id, platform_family, endpoint_id,
            native_scope_id, resource_kind, native_id)
        ELSE true END);
