-- Native intent is a durable business fact. A claimed intent is never retried
-- without independent observation and operator reconciliation. Apply after
-- worker grants (0004); no external platform call occurs in this transaction.
-- This mapping is created for an already observed B06 native binding before
-- issuing a B10 grant. Planned resources without a native ID remain unsupported.
CREATE TABLE hosting_controlplane.native_operation_leases (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    lease_key text NOT NULL,
    job_id text NOT NULL,
    operation_id text NOT NULL,
    platform_family text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    resource_kind text NOT NULL,
    native_id text NOT NULL,
    site_id text NOT NULL,
    security_domain_id text NOT NULL,
    worker_id text NOT NULL,
    owner_epoch bigint NOT NULL CHECK (owner_epoch > 0),
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, lease_key),
    UNIQUE (organization_id, tenant_id, job_id, operation_id),
    FOREIGN KEY (organization_id, tenant_id, job_id)
        REFERENCES hosting_controlplane.operation_jobs
        (organization_id, tenant_id, job_id) ON DELETE RESTRICT,
    FOREIGN KEY (platform_family, endpoint_id, native_scope_id,
                 resource_kind, native_id)
        REFERENCES hosting_controlplane.native_ownership
        (platform_family, endpoint_id, native_scope_id, resource_kind, native_id)
        ON DELETE RESTRICT
);

CREATE TABLE hosting_controlplane.native_operation_intents (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    operation_id text NOT NULL,
    job_id text NOT NULL,
    grant_id text NOT NULL,
    step_id text NOT NULL,
    lease_key text NOT NULL,
    platform_family text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    resource_kind text NOT NULL,
    native_id text NOT NULL,
    workload_id text NOT NULL,
    security_domain_id text NOT NULL,
    worker_id text NOT NULL,
    owner_epoch bigint NOT NULL CHECK (owner_epoch > 0),
    operation_kind text NOT NULL,
    request_digest text NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    state text NOT NULL DEFAULT 'PREPARED' CHECK (state IN
        ('PREPARED', 'IN_FLIGHT', 'TASK_ACCEPTED', 'UNCERTAIN', 'RESOLVED')),
    native_task_id text,
    outcome text CHECK (outcome IN ('NO_EFFECT', 'EFFECT_PRESENT')),
    resolution_evidence_digest text CHECK
        (resolution_evidence_digest ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, operation_id),
    FOREIGN KEY (organization_id, tenant_id, job_id)
        REFERENCES hosting_controlplane.operation_jobs
        (organization_id, tenant_id, job_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, tenant_id, lease_key)
        REFERENCES hosting_controlplane.native_operation_leases
        (organization_id, tenant_id, lease_key) ON DELETE RESTRICT,
    CHECK (native_task_id IS NULL OR length(native_task_id) BETWEEN 1 AND 512),
    CHECK ((state = 'RESOLVED') =
        (outcome IS NOT NULL AND resolution_evidence_digest IS NOT NULL))
);
-- Also serializes an operation against an identical native identity in a
-- different tenant. The owner row has a global key; the transaction locks it.
CREATE UNIQUE INDEX native_operation_unresolved_binding
    ON hosting_controlplane.native_operation_intents
    (platform_family, endpoint_id, native_scope_id, resource_kind, native_id)
    WHERE state != 'RESOLVED';
CREATE INDEX native_operation_job
    ON hosting_controlplane.native_operation_intents
    (organization_id, tenant_id, job_id, operation_id);

CREATE TABLE hosting_controlplane.native_operation_observations (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    observation_id text NOT NULL,
    operation_id text NOT NULL,
    evidence_digest text NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
    observer_subject text NOT NULL,
    native_task_id text,
    outcome text NOT NULL CHECK
        (outcome IN ('UNKNOWN', 'IN_PROGRESS', 'NO_EFFECT', 'EFFECT_PRESENT')),
    native_quiesced boolean NOT NULL,
    observed_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, observation_id),
    UNIQUE (organization_id, tenant_id, observation_id, operation_id),
    FOREIGN KEY (organization_id, tenant_id, operation_id)
        REFERENCES hosting_controlplane.native_operation_intents
        (organization_id, tenant_id, operation_id) ON DELETE RESTRICT
);
CREATE INDEX native_observations_operation
    ON hosting_controlplane.native_operation_observations
    (organization_id, tenant_id, operation_id, recorded_at DESC);

CREATE TABLE hosting_controlplane.native_operation_reviews (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    operation_id text NOT NULL,
    reviewer_subject text NOT NULL,
    observation_id text NOT NULL,
    evidence_digest text NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
    decision text NOT NULL CHECK (decision IN ('NO_EFFECT', 'EFFECT_PRESENT')),
    incident_id text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, operation_id, reviewer_subject),
    FOREIGN KEY (organization_id, tenant_id, operation_id)
        REFERENCES hosting_controlplane.native_operation_intents
        (organization_id, tenant_id, operation_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, tenant_id, observation_id, operation_id)
        REFERENCES hosting_controlplane.native_operation_observations
        (organization_id, tenant_id, observation_id, operation_id) ON DELETE RESTRICT
);

CREATE TABLE hosting_controlplane.native_owner_recovery_reviews (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    platform_family text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    resource_kind text NOT NULL,
    native_id text NOT NULL,
    owner_epoch bigint NOT NULL CHECK (owner_epoch > 0),
    reviewer_subject text NOT NULL,
    old_worker_id text NOT NULL,
    native_evidence_digest text NOT NULL CHECK
        (native_evidence_digest ~ '^[0-9a-f]{64}$'),
    worker_fence_digest text NOT NULL CHECK
        (worker_fence_digest ~ '^[0-9a-f]{64}$'),
    observed_at timestamptz NOT NULL,
    incident_id text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, platform_family, endpoint_id,
                 native_scope_id, resource_kind, native_id, owner_epoch,
                 reviewer_subject),
    FOREIGN KEY (platform_family, endpoint_id, native_scope_id,
                 resource_kind, native_id)
        REFERENCES hosting_controlplane.native_ownership
        (platform_family, endpoint_id, native_scope_id, resource_kind, native_id)
        ON DELETE RESTRICT
);

-- Incident containment takes precedence over any successful observation or
-- reconciliation. Clearing it belongs to a separate incident authority path.
CREATE TABLE hosting_controlplane.native_containment_holds (
    platform_family text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    resource_kind text NOT NULL,
    native_id text NOT NULL,
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    incident_id text NOT NULL,
    actor_subject text NOT NULL,
    reason text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (platform_family, endpoint_id, native_scope_id,
                 resource_kind, native_id),
    FOREIGN KEY (platform_family, endpoint_id, native_scope_id,
                 resource_kind, native_id)
        REFERENCES hosting_controlplane.native_ownership
        (platform_family, endpoint_id, native_scope_id, resource_kind, native_id)
        ON DELETE RESTRICT
);

CREATE FUNCTION hosting_controlplane.guard_native_operation_intent()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.organization_id, NEW.tenant_id, NEW.operation_id, NEW.job_id,
        NEW.grant_id, NEW.step_id, NEW.lease_key,
        NEW.platform_family, NEW.endpoint_id, NEW.native_scope_id,
        NEW.resource_kind, NEW.native_id, NEW.workload_id,
        NEW.security_domain_id, NEW.worker_id, NEW.owner_epoch,
        NEW.operation_kind, NEW.request_digest, NEW.created_at) IS DISTINCT FROM
       (OLD.organization_id, OLD.tenant_id, OLD.operation_id, OLD.job_id,
        OLD.grant_id, OLD.step_id, OLD.lease_key,
        OLD.platform_family, OLD.endpoint_id, OLD.native_scope_id,
        OLD.resource_kind, OLD.native_id, OLD.workload_id,
        OLD.security_domain_id, OLD.worker_id, OLD.owner_epoch,
        OLD.operation_kind, OLD.request_digest, OLD.created_at) THEN
        RAISE EXCEPTION 'Native operation intent binding is immutable';
    END IF;
    IF (OLD.state, NEW.state) NOT IN
       (('PREPARED', 'IN_FLIGHT'), ('IN_FLIGHT', 'TASK_ACCEPTED'),
        ('IN_FLIGHT', 'UNCERTAIN'), ('TASK_ACCEPTED', 'UNCERTAIN'),
        ('UNCERTAIN', 'RESOLVED'), ('TASK_ACCEPTED', 'RESOLVED')) THEN
        RAISE EXCEPTION 'Native operation state transition is forbidden';
    END IF;
    IF (OLD.native_task_id IS DISTINCT FROM NEW.native_task_id
        AND NOT (OLD.state = 'IN_FLIGHT' AND NEW.state = 'TASK_ACCEPTED'
                 AND OLD.native_task_id IS NULL AND NEW.native_task_id IS NOT NULL))
        OR (NEW.state = 'TASK_ACCEPTED' AND NEW.native_task_id IS NULL)
        OR (NEW.state != 'RESOLVED' AND
            (NEW.outcome IS NOT NULL OR NEW.resolution_evidence_digest IS NOT NULL)) THEN
        RAISE EXCEPTION 'Native task or resolution fields cannot be rewritten';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER native_intent_guard BEFORE UPDATE
    ON hosting_controlplane.native_operation_intents
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_native_operation_intent();

-- B06's ordinary live-lease release must also respect B11's unresolved work.
-- An expired lease cannot be released through that path already; this trigger
-- prevents a live release and immediate new owner during a native timeout.
CREATE FUNCTION hosting_controlplane.guard_native_owner_release()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.worker_id IS DISTINCT FROM OLD.worker_id
        OR NEW.lease_epoch IS DISTINCT FROM OLD.lease_epoch
        OR NEW.lease_expires_at IS DISTINCT FROM OLD.lease_expires_at)
       AND EXISTS (
           SELECT 1 FROM hosting_controlplane.native_containment_holds h
           WHERE h.platform_family = OLD.platform_family
             AND h.endpoint_id = OLD.endpoint_id
             AND h.native_scope_id = OLD.native_scope_id
             AND h.resource_kind = OLD.resource_kind
             AND h.native_id = OLD.native_id) THEN
        RAISE EXCEPTION 'Incident containment blocks owner lease transition';
    END IF;
    IF (NEW.worker_id IS DISTINCT FROM OLD.worker_id
        OR NEW.lease_epoch IS DISTINCT FROM OLD.lease_epoch
        OR NEW.lease_expires_at IS NULL AND OLD.lease_expires_at IS NOT NULL)
       AND EXISTS (
           SELECT 1 FROM hosting_controlplane.native_operation_intents i
           WHERE i.platform_family = OLD.platform_family
             AND i.endpoint_id = OLD.endpoint_id
             AND i.native_scope_id = OLD.native_scope_id
             AND i.resource_kind = OLD.resource_kind
             AND i.native_id = OLD.native_id
             AND i.state != 'RESOLVED') THEN
        RAISE EXCEPTION 'Unresolved native operation blocks owner transition';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER native_owner_operation_guard BEFORE UPDATE
    ON hosting_controlplane.native_ownership
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_native_owner_release();

CREATE FUNCTION hosting_controlplane.guard_native_operation_lease()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Native operation lease mapping is immutable';
END;
$$;
CREATE TRIGGER native_operation_lease_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.native_operation_leases
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_native_operation_lease();

CREATE TRIGGER native_observation_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.native_operation_observations
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER native_review_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.native_operation_reviews
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER native_recovery_review_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.native_owner_recovery_reviews
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER native_containment_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.native_containment_holds
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'native_operation_leases',
        'native_operation_intents', 'native_operation_observations',
        'native_operation_reviews', 'native_owner_recovery_reviews',
        'native_containment_holds'] LOOP
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
