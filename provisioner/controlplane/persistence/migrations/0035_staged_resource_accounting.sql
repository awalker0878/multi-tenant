-- A newly approved staged cutover references the original allocation owner.
-- It never creates/rekeys a capacity reservation or rewrites the old job.
CREATE TABLE hosting_controlplane.staged_resource_accounting_bindings (
    organization_id text NOT NULL, tenant_id text NOT NULL,
    job_id text NOT NULL, original_job_id text NOT NULL,
    current_selection_digest text NOT NULL CHECK(current_selection_digest ~ '^[0-9a-f]{64}$'),
    original_selection_digest text NOT NULL CHECK(original_selection_digest ~ '^[0-9a-f]{64}$'),
    original_plan_digest text NOT NULL CHECK(original_plan_digest ~ '^[0-9a-f]{64}$'),
    resource_bundle_digest text NOT NULL CHECK(resource_bundle_digest ~ '^[0-9a-f]{64}$'),
    reservation_digest text NOT NULL CHECK(reservation_digest ~ '^[0-9a-f]{64}$'),
    handover_digest text NOT NULL CHECK(handover_digest ~ '^[0-9a-f]{64}$'),
    binding_digest text NOT NULL CHECK(binding_digest ~ '^[0-9a-f]{64}$'),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(organization_id,tenant_id,job_id),
    CHECK(job_id <> original_job_id),
    FOREIGN KEY(organization_id,tenant_id,job_id)
        REFERENCES hosting_controlplane.operation_jobs(organization_id,tenant_id,job_id) ON DELETE RESTRICT,
    FOREIGN KEY(organization_id,tenant_id,original_job_id)
        REFERENCES hosting_controlplane.operation_jobs(organization_id,tenant_id,job_id) ON DELETE RESTRICT
);
REVOKE ALL ON hosting_controlplane.staged_resource_accounting_bindings FROM PUBLIC;
ALTER TABLE hosting_controlplane.staged_resource_accounting_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.staged_resource_accounting_bindings FORCE ROW LEVEL SECURITY;
CREATE POLICY staged_accounting_tenant ON hosting_controlplane.staged_resource_accounting_bindings
    USING(organization_id=current_setting('app.organization_id',true) AND tenant_id=current_setting('app.tenant_id',true))
    WITH CHECK(organization_id=current_setting('app.organization_id',true) AND tenant_id=current_setting('app.tenant_id',true));
CREATE TRIGGER staged_accounting_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.staged_resource_accounting_bindings FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

-- The current service projection still uses the original B10/B11 lease and
-- intent tables. Its explicit staged purpose can never become VM_CREATE.
CREATE FUNCTION hosting_controlplane.prevent_staged_recreation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.operation_kind='VM_CREATE' AND EXISTS(
        SELECT 1 FROM hosting_controlplane.staged_resource_accounting_bindings s
         WHERE (s.organization_id,s.tenant_id,s.job_id)=
               (NEW.organization_id,NEW.tenant_id,NEW.job_id)
    ) THEN RAISE EXCEPTION 'Staged resource accounting cannot authorize another native creation'; END IF;
    RETURN NEW;
END; $$;
CREATE TRIGGER staged_no_recreation BEFORE INSERT
    ON hosting_controlplane.native_operation_intents FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.prevent_staged_recreation();
