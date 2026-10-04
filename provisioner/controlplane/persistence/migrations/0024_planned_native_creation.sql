-- Extend the existing native intent owner to creation, before native IDs exist.
-- A planned identity is explicitly distinct from a native identity. No fixture
-- or generated native ID is put into native_ownership. Accepted/unknown effects
-- remain in the same B11 native_operation_intents journal.
CREATE TABLE hosting_controlplane.planned_resource_ownership (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    job_id text NOT NULL,
    resource_id text NOT NULL,
    selection_digest text NOT NULL CHECK (selection_digest ~ '^[0-9a-f]{64}$'),
    request_digest text NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    reservation_digest text NOT NULL CHECK (reservation_digest ~ '^[0-9a-f]{64}$'),
    resource_kind text NOT NULL CHECK (resource_kind IN ('vm', 'deployment')),
    platform_family text NOT NULL CHECK (platform_family = 'openstack'),
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    site_id text NOT NULL,
    security_domain_id text NOT NULL,
    workload_id text NOT NULL,
    worker_id text NOT NULL,
    owner_epoch bigint NOT NULL CHECK (owner_epoch > 0),
    lease_expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, job_id, resource_id),
    FOREIGN KEY (organization_id, tenant_id, job_id)
        REFERENCES hosting_controlplane.operation_jobs
        (organization_id, tenant_id, job_id) ON DELETE RESTRICT
);
-- A new plan/job cannot evade an earlier unresolved creation by naming the
-- same workload/target in this native scope. Tombstoned planned identities
-- require a new approved target identity; expiry never provides reuse.
CREATE UNIQUE INDEX planned_resource_exact_native_intent
    ON hosting_controlplane.planned_resource_ownership
    (platform_family, endpoint_id, native_scope_id, workload_id, resource_id);

-- An aggregate deployment and an individual VM must not reserve the same
-- logical target twice. This immutable projection belongs to the planned
-- owner above; it is neither another operation journal nor native ownership.
CREATE TABLE hosting_controlplane.planned_creation_children (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    job_id text NOT NULL,
    resource_id text NOT NULL,
    platform_family text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    workload_id text NOT NULL,
    target_machine_id text NOT NULL,
    PRIMARY KEY (organization_id, tenant_id, job_id, resource_id, target_machine_id),
    UNIQUE (platform_family, endpoint_id, native_scope_id, workload_id, target_machine_id),
    FOREIGN KEY (organization_id, tenant_id, job_id, resource_id)
        REFERENCES hosting_controlplane.planned_resource_ownership
        (organization_id, tenant_id, job_id, resource_id) ON DELETE RESTRICT
);
CREATE FUNCTION hosting_controlplane.guard_planned_child_scope()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.planned_resource_ownership p
         WHERE (p.organization_id, p.tenant_id, p.job_id, p.resource_id,
                p.platform_family, p.endpoint_id, p.native_scope_id, p.workload_id) =
               (NEW.organization_id, NEW.tenant_id, NEW.job_id, NEW.resource_id,
                NEW.platform_family, NEW.endpoint_id, NEW.native_scope_id, NEW.workload_id)
    ) THEN
        RAISE EXCEPTION 'Planned child must project the exact immutable owner scope';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER planned_child_scope BEFORE INSERT
    ON hosting_controlplane.planned_creation_children
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_planned_child_scope();
CREATE TRIGGER planned_child_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.planned_creation_children
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

ALTER TABLE hosting_controlplane.native_operation_leases
    ALTER COLUMN native_id DROP NOT NULL,
    ADD COLUMN planned_resource_id text,
    ADD CONSTRAINT operation_lease_identity_kind CHECK (
        (native_id IS NOT NULL AND planned_resource_id IS NULL) OR
        (native_id IS NULL AND planned_resource_id IS NOT NULL)),
    ADD CONSTRAINT operation_lease_planned_owner FOREIGN KEY
        (organization_id, tenant_id, job_id, planned_resource_id)
        REFERENCES hosting_controlplane.planned_resource_ownership
        (organization_id, tenant_id, job_id, resource_id) ON DELETE RESTRICT;

ALTER TABLE hosting_controlplane.native_operation_intents
    ALTER COLUMN native_id DROP NOT NULL,
    ADD COLUMN planned_resource_id text,
    ADD CONSTRAINT operation_intent_identity_kind CHECK (
        (native_id IS NOT NULL AND planned_resource_id IS NULL) OR
        (native_id IS NULL AND planned_resource_id IS NOT NULL)),
    ADD CONSTRAINT operation_intent_planned_owner FOREIGN KEY
        (organization_id, tenant_id, job_id, planned_resource_id)
        REFERENCES hosting_controlplane.planned_resource_ownership
        (organization_id, tenant_id, job_id, resource_id) ON DELETE RESTRICT;
CREATE UNIQUE INDEX planned_operation_unresolved_binding
    ON hosting_controlplane.native_operation_intents
    (organization_id, tenant_id, job_id, planned_resource_id)
    WHERE state != 'RESOLVED' AND planned_resource_id IS NOT NULL;

CREATE FUNCTION hosting_controlplane.guard_planned_operation_scope()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.planned_resource_id IS NULL THEN
        RETURN NEW;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.planned_resource_ownership p
         WHERE (p.organization_id, p.tenant_id, p.job_id, p.resource_id,
                p.platform_family, p.endpoint_id, p.native_scope_id, p.resource_kind,
                p.worker_id, p.owner_epoch, p.security_domain_id) =
               (NEW.organization_id, NEW.tenant_id, NEW.job_id, NEW.planned_resource_id,
                NEW.platform_family, NEW.endpoint_id, NEW.native_scope_id, NEW.resource_kind,
                NEW.worker_id, NEW.owner_epoch, NEW.security_domain_id)
    ) THEN
        RAISE EXCEPTION 'Planned operation must project its exact immutable owner';
    END IF;
    IF TG_TABLE_NAME = 'native_operation_leases' THEN
        IF NOT EXISTS (
            SELECT 1 FROM hosting_controlplane.planned_resource_ownership p
             WHERE (p.organization_id, p.tenant_id, p.job_id, p.resource_id) =
                   (NEW.organization_id, NEW.tenant_id, NEW.job_id, NEW.planned_resource_id)
               AND p.site_id = NEW.site_id AND NEW.expires_at <= p.lease_expires_at
        ) THEN
            RAISE EXCEPTION 'Planned operation lease exceeds its owner scope or deadline';
        END IF;
    ELSE
        IF NEW.operation_kind <> 'VM_CREATE' OR NOT EXISTS (
            SELECT 1 FROM hosting_controlplane.planned_resource_ownership p
            JOIN hosting_controlplane.native_operation_leases l
              ON (p.organization_id, p.tenant_id, p.job_id, p.resource_id) =
                 (l.organization_id, l.tenant_id, l.job_id, l.planned_resource_id)
             WHERE (p.organization_id, p.tenant_id, p.job_id, p.resource_id,
                    p.workload_id, p.request_digest, l.lease_key, l.operation_id) =
                   (NEW.organization_id, NEW.tenant_id, NEW.job_id, NEW.planned_resource_id,
                    NEW.workload_id, NEW.request_digest, NEW.lease_key, NEW.operation_id)
        ) THEN
            RAISE EXCEPTION 'Only the exact leased planned VM_CREATE request is allowed';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER planned_lease_scope BEFORE INSERT
    ON hosting_controlplane.native_operation_leases
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_planned_operation_scope();
CREATE TRIGGER planned_native_intent_scope BEFORE INSERT
    ON hosting_controlplane.native_operation_intents
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_planned_operation_scope();

CREATE FUNCTION hosting_controlplane.guard_planned_creation_identity()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'Planned creation ownership is immutable; expiry never grants a new writer';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER planned_creation_identity BEFORE UPDATE
    ON hosting_controlplane.planned_resource_ownership
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_planned_creation_identity();
CREATE TRIGGER planned_creation_no_delete BEFORE DELETE
    ON hosting_controlplane.planned_resource_ownership
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

-- Real identities enter only after independently authenticated native
-- readback. They remain observations in the existing intent owner's journal;
-- they do not rewrite an immutable pre-creation identity into a native one.
ALTER TABLE hosting_controlplane.native_operation_observations
    ADD COLUMN created_native_bindings jsonb,
    ADD CONSTRAINT observed_creation_native_identity CHECK (
        created_native_bindings IS NULL OR (
            outcome = 'EFFECT_PRESENT' AND
            jsonb_typeof(created_native_bindings) = 'array' AND
            jsonb_array_length(created_native_bindings) > 0));

CREATE FUNCTION hosting_controlplane.guard_planned_intent_binding()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.planned_resource_id IS DISTINCT FROM OLD.planned_resource_id THEN
        RAISE EXCEPTION 'Planned operation identity is immutable';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER planned_intent_binding BEFORE UPDATE
    ON hosting_controlplane.native_operation_intents
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_planned_intent_binding();

ALTER TABLE hosting_controlplane.planned_resource_ownership ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.planned_resource_ownership FORCE ROW LEVEL SECURITY;
CREATE POLICY planned_creation_tenant ON hosting_controlplane.planned_resource_ownership
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true));
REVOKE ALL ON hosting_controlplane.planned_resource_ownership FROM PUBLIC;
ALTER TABLE hosting_controlplane.planned_creation_children ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.planned_creation_children FORCE ROW LEVEL SECURITY;
CREATE POLICY planned_child_tenant ON hosting_controlplane.planned_creation_children
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true));
REVOKE ALL ON hosting_controlplane.planned_creation_children FROM PUBLIC;

-- This function exposes only a caller-tenant mapping. It does not enroll or
-- issue a worker grant, update an ownership epoch, or authorize a native call.
CREATE FUNCTION hosting_controlplane.lock_planned_worker_scope(
    selected_organization text, selected_tenant text, selected_lease text)
RETURNS TABLE (
    job_id text, operation_id text, resource_id text, resource_kind text,
    platform_family text, endpoint_id text, native_scope_id text, site_id text,
    security_domain_id text, worker_id text, owner_epoch bigint,
    expires_at timestamptz, owner_expires_at timestamptz,
    selection_digest text, request_digest text, reservation_digest text)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
BEGIN
    IF current_setting('app.organization_id', true) IS DISTINCT FROM selected_organization
       OR current_setting('app.tenant_id', true) IS DISTINCT FROM selected_tenant THEN
        RAISE EXCEPTION 'Verified tenant context is required' USING ERRCODE = '42501';
    END IF;
    IF pg_catalog.pg_has_role(session_user, 'hosting_site_worker_roles', 'member')
       OR hosting_controlplane.is_site_worker_role() THEN
        RAISE EXCEPTION 'Read-only site worker cannot lock a creation scope'
            USING ERRCODE = '42501';
    END IF;
    RETURN QUERY SELECT l.job_id, l.operation_id, p.resource_id, p.resource_kind,
           p.platform_family, p.endpoint_id, p.native_scope_id, p.site_id,
           p.security_domain_id, p.worker_id, p.owner_epoch,
           l.expires_at, p.lease_expires_at,
           p.selection_digest, p.request_digest, p.reservation_digest
      FROM hosting_controlplane.native_operation_leases l
      JOIN hosting_controlplane.planned_resource_ownership p
        ON (p.organization_id, p.tenant_id, p.job_id, p.resource_id) =
           (l.organization_id, l.tenant_id, l.job_id, l.planned_resource_id)
     WHERE l.organization_id = selected_organization AND l.tenant_id = selected_tenant
       AND l.lease_key = selected_lease
       AND l.native_id IS NULL
     FOR SHARE OF l, p;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_planned_worker_scope(text,text,text) FROM PUBLIC;
