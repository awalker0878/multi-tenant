-- Apply after 0002_jobs.sql. Runtime credentials need SELECT on these tables;
-- only the authority writer may INSERT approvals or UPDATE epoch. Never grant
-- direct authority-table DML to the HTTP or worker database roles.
-- The migration/function owner MUST be NOSUPERUSER NOBYPASSRLS: FORCE RLS does
-- not constrain a superuser-owned SECURITY DEFINER function. Tenant GUCs are
-- defense in depth, not authentication of a caller with arbitrary SQL access.

CREATE TABLE hosting_controlplane.plan_authority_state (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    plan_id text NOT NULL,
    plan_kind text GENERATED ALWAYS AS ('MigrationPlan'::text) STORED,
    plan_revision bigint NOT NULL CHECK (plan_revision > 0),
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[0-9a-f]{64}$'),
    revocation_epoch bigint NOT NULL DEFAULT 0 CHECK (revocation_epoch >= 0),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, plan_id),
    FOREIGN KEY (organization_id, tenant_id, plan_kind, plan_id)
        REFERENCES hosting_controlplane.enterprise_records
        (organization_id, tenant_id, record_kind, record_id) ON DELETE RESTRICT
);

-- Existing validated plans start with no approvals at epoch zero. The trigger
-- advances the epoch in the plan update transaction, invalidating old grants.
-- The migration transaction takes an exclusive DDL lock. Temporarily disable
-- source-table RLS for the owner-only backfill; re-enable before commit so no
-- runtime transaction can observe a relaxed policy.
ALTER TABLE hosting_controlplane.enterprise_records DISABLE ROW LEVEL SECURITY;
INSERT INTO hosting_controlplane.plan_authority_state
    (organization_id, tenant_id, plan_id, plan_revision, plan_digest)
SELECT organization_id, tenant_id, record_id, revision,
       record_json->'metadata'->>'planDigest'
FROM hosting_controlplane.enterprise_records
WHERE record_kind = 'MigrationPlan';
ALTER TABLE hosting_controlplane.enterprise_records ENABLE ROW LEVEL SECURITY;

CREATE FUNCTION hosting_controlplane.sync_plan_authority_state()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
BEGIN
    IF NEW.record_kind = 'MigrationPlan' THEN
        INSERT INTO hosting_controlplane.plan_authority_state
            (organization_id, tenant_id, plan_id, plan_revision, plan_digest)
        VALUES (NEW.organization_id, NEW.tenant_id, NEW.record_id,
                NEW.revision, NEW.record_json->'metadata'->>'planDigest')
        ON CONFLICT (organization_id, tenant_id, plan_id) DO UPDATE
        SET plan_revision = EXCLUDED.plan_revision,
            plan_digest = EXCLUDED.plan_digest,
            revocation_epoch = hosting_controlplane.plan_authority_state.revocation_epoch
                + CASE WHEN
                    hosting_controlplane.plan_authority_state.plan_revision != EXCLUDED.plan_revision
                    OR hosting_controlplane.plan_authority_state.plan_digest != EXCLUDED.plan_digest
                    THEN 1 ELSE 0 END,
            updated_at = clock_timestamp();
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER plan_revision_invalidates_authority
    AFTER INSERT OR UPDATE OF revision, record_json
    ON hosting_controlplane.enterprise_records
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.sync_plan_authority_state();

-- PostgreSQL SELECT FOR SHARE requires UPDATE privilege. Expose exactly the
-- locking operation through a definer function, not UPDATE rights on immutable
-- approvals or general plan records. The owner is still subject to FORCE RLS;
-- both scoped transaction settings must match explicit arguments.
CREATE FUNCTION hosting_controlplane.lock_authority_scope(
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
    SELECT s.plan_revision, s.plan_digest, s.revocation_epoch
    INTO current_revision, current_digest, current_epoch
    FROM hosting_controlplane.plan_authority_state s
    WHERE s.organization_id = p_organization_id AND s.tenant_id = p_tenant_id
      AND s.plan_id = p_plan_id FOR SHARE;
    IF NOT FOUND THEN
        RETURN;
    END IF;
    SELECT e.record_json->'spec'->>'workloadId' INTO workload_id
    FROM hosting_controlplane.enterprise_records e
    WHERE e.organization_id = p_organization_id AND e.tenant_id = p_tenant_id
      AND e.record_kind = 'MigrationPlan' AND e.record_id = p_plan_id;
    IF workload_id IS NULL THEN
        RETURN;
    END IF;
    PERFORM 1 FROM hosting_controlplane.enterprise_records w
    WHERE w.organization_id = p_organization_id AND w.tenant_id = p_tenant_id
      AND w.record_kind = 'Workload' AND w.record_id = workload_id FOR SHARE;
    IF NOT FOUND THEN
        RETURN;
    END IF;
    RETURN QUERY SELECT current_revision, current_digest, current_epoch;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_authority_scope(text, text, text)
    FROM PUBLIC;

CREATE TABLE hosting_controlplane.plan_approvals (
    approval_id text PRIMARY KEY,
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    plan_id text NOT NULL,
    plan_revision bigint NOT NULL CHECK (plan_revision > 0),
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[0-9a-f]{64}$'),
    revocation_epoch bigint NOT NULL CHECK (revocation_epoch >= 0),
    role text NOT NULL CHECK (role IN
        ('SOURCE_OWNER', 'DESTINATION_OWNER', 'SOURCE_SECURITY', 'DESTINATION_SECURITY')),
    site_id text NOT NULL,
    security_domain_id text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    platform_family text NOT NULL,
    approver_subject text NOT NULL CHECK (length(approver_subject) > 0),
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    FOREIGN KEY (organization_id, tenant_id, plan_id)
        REFERENCES hosting_controlplane.plan_authority_state
        (organization_id, tenant_id, plan_id) ON DELETE RESTRICT,
    UNIQUE (organization_id, tenant_id, plan_id, revocation_epoch, role),
    UNIQUE (organization_id, tenant_id, plan_id, revocation_epoch, approver_subject),
    CHECK (expires_at > issued_at AND expires_at <= issued_at + interval '8 hours')
);
CREATE INDEX plan_approvals_current
    ON hosting_controlplane.plan_approvals
    (organization_id, tenant_id, plan_id, revocation_epoch);

CREATE TABLE hosting_controlplane.plan_revocations (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    plan_id text NOT NULL,
    from_epoch bigint NOT NULL CHECK (from_epoch >= 0),
    to_epoch bigint NOT NULL CHECK (to_epoch = from_epoch + 1),
    actor_subject text NOT NULL CHECK (length(actor_subject) > 0),
    reason text NOT NULL CHECK (length(reason) > 0),
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (organization_id, tenant_id, plan_id)
        REFERENCES hosting_controlplane.plan_authority_state
        (organization_id, tenant_id, plan_id) ON DELETE RESTRICT,
    UNIQUE (organization_id, tenant_id, plan_id, to_epoch)
);

CREATE TRIGGER approvals_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.plan_approvals
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER revocations_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.plan_revocations
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['plan_authority_state', 'plan_approvals',
                                       'plan_revocations'] LOOP
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
