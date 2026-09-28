-- A workflow start may have succeeded even when its response was lost. Record
-- the first external attempt before contacting Temporal, and keep the accepted
-- run identity permanently with the outbox intent.
ALTER TABLE hosting_controlplane.job_outbox
    ADD COLUMN start_namespace text,
    ADD COLUMN first_start_attempted_at timestamptz,
    ADD COLUMN start_retention_until timestamptz,
    ADD COLUMN start_payload_digest text CHECK
        (start_payload_digest ~ '^[0-9a-f]{64}$'),
    ADD COLUMN start_run_id text,
    ADD CONSTRAINT outbox_start_binding_complete CHECK (
        (start_namespace IS NULL AND first_start_attempted_at IS NULL
         AND start_retention_until IS NULL AND start_payload_digest IS NULL)
        OR (start_namespace IS NOT NULL AND first_start_attempted_at IS NOT NULL
            AND start_retention_until IS NOT NULL AND start_payload_digest IS NOT NULL
            AND start_retention_until > first_start_attempted_at)),
    ADD CONSTRAINT outbox_run_requires_start CHECK
        (start_run_id IS NULL OR first_start_attempted_at IS NOT NULL);

CREATE FUNCTION hosting_controlplane.guard_job_outbox_start_binding()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.first_start_attempted_at IS NOT NULL AND
       (NEW.start_namespace, NEW.first_start_attempted_at,
        NEW.start_retention_until, NEW.start_payload_digest) IS DISTINCT FROM
       (OLD.start_namespace, OLD.first_start_attempted_at,
        OLD.start_retention_until, OLD.start_payload_digest) THEN
        RAISE EXCEPTION 'Workflow start attempt binding is immutable';
    END IF;
    IF OLD.start_run_id IS NOT NULL AND NEW.start_run_id IS DISTINCT FROM OLD.start_run_id THEN
        RAISE EXCEPTION 'Durable workflow run ID is immutable';
    END IF;
    IF OLD.delivered_at IS NOT NULL AND NEW.delivered_at IS DISTINCT FROM OLD.delivered_at THEN
        RAISE EXCEPTION 'Delivered workflow outbox intent is immutable';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER job_outbox_start_binding_guard BEFORE UPDATE
    ON hosting_controlplane.job_outbox
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_job_outbox_start_binding();
