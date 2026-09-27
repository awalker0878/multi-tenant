-- Job admission and workflow-start outbox. Apply after 0001_controlplane.sql.
-- All tables are tenant scoped, including the progress-event projection.
CREATE TABLE hosting_controlplane.operation_jobs (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    job_id text NOT NULL,
    idempotency_key text NOT NULL,
    plan_id text NOT NULL,
    plan_kind text GENERATED ALWAYS AS ('MigrationPlan'::text) STORED,
    plan_revision bigint NOT NULL CHECK (plan_revision > 0),
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[0-9a-f]{64}$'),
    source_scope jsonb NOT NULL CHECK (jsonb_typeof(source_scope) = 'object'),
    destination_scope jsonb NOT NULL CHECK (jsonb_typeof(destination_scope) = 'object'),
    actor_subject text NOT NULL,
    approval_ids jsonb NOT NULL CHECK (jsonb_typeof(approval_ids) = 'array'),
    revocation_epoch bigint NOT NULL CHECK (revocation_epoch >= 0),
    status text NOT NULL DEFAULT 'QUEUED',
    last_event_sequence bigint NOT NULL DEFAULT 1 CHECK (last_event_sequence > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, tenant_id, job_id),
    UNIQUE (organization_id, tenant_id, idempotency_key),
    UNIQUE (organization_id, tenant_id, plan_id, plan_revision, plan_digest),
    FOREIGN KEY (organization_id, tenant_id, plan_kind, plan_id)
        REFERENCES hosting_controlplane.enterprise_records
        (organization_id, tenant_id, record_kind, record_id) ON DELETE RESTRICT,
    CONSTRAINT operation_jobs_status CHECK (status IN
        ('QUEUED', 'START_REQUESTED', 'STARTED', 'WAITING_APPROVAL',
         'RUNNING', 'HELD', 'SUCCEEDED', 'FAILED', 'CANCELLED'))
);

CREATE TABLE hosting_controlplane.job_events (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    job_id text NOT NULL,
    sequence bigint NOT NULL CHECK (sequence > 0),
    event_key text NOT NULL,
    event_type text NOT NULL,
    status text NOT NULL,
    detail jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(detail) = 'object'),
    recorded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, tenant_id, job_id, sequence),
    UNIQUE (organization_id, tenant_id, job_id, event_key),
    FOREIGN KEY (organization_id, tenant_id, job_id)
        REFERENCES hosting_controlplane.operation_jobs (organization_id, tenant_id, job_id)
        ON DELETE RESTRICT
);

CREATE TABLE hosting_controlplane.job_outbox (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    outbox_id text NOT NULL,
    job_id text NOT NULL,
    event_type text NOT NULL CHECK (event_type = 'START_WORKFLOW'),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    claim_token text,
    claimed_by text,
    claimed_until timestamptz,
    attempts bigint NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    delivered_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, tenant_id, outbox_id),
    UNIQUE (organization_id, tenant_id, job_id, event_type),
    FOREIGN KEY (organization_id, tenant_id, job_id)
        REFERENCES hosting_controlplane.operation_jobs (organization_id, tenant_id, job_id)
        ON DELETE RESTRICT,
    CONSTRAINT outbox_claim_consistent CHECK (
        (claim_token IS NULL AND claimed_by IS NULL AND claimed_until IS NULL)
        OR (claim_token IS NOT NULL AND claimed_by IS NOT NULL AND claimed_until IS NOT NULL))
);

CREATE INDEX job_outbox_due_idx
    ON hosting_controlplane.job_outbox (organization_id, tenant_id, claimed_until, created_at)
    WHERE delivered_at IS NULL;

-- FORCE applies even if the service happens to own a table. Use a separate
-- migration role for DDL, and a non-BYPASSRLS runtime role for DML.
DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['operation_jobs', 'job_events', 'job_outbox'] LOOP
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
