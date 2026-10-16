-- CT-02: Planning-owned durable Assurance invalidation inbox.
-- Hints can only hold planning decisions; they never grant native authority.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE planning_owner;

CREATE TABLE app.planning_qualification_inbox (
    event_id uuid PRIMARY KEY REFERENCES app.planning_fact_inbox(event_id),
    tenant uuid NOT NULL,
    scope_sha256 text NOT NULL CHECK (scope_sha256 ~ '^[0-9a-f]{64}$'),
    authority_epoch bigint NOT NULL CHECK (authority_epoch >= 1),
    event_sha256 text NOT NULL CHECK (event_sha256 ~ '^[0-9a-f]{64}$'),
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    state text NOT NULL CHECK (state IN ('qualified', 'suspended', 'revoked')),
    received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (scope_sha256, authority_epoch)
);

CREATE TABLE app.planning_qualification_heads (
    scope_sha256 text PRIMARY KEY CHECK (scope_sha256 ~ '^[0-9a-f]{64}$'),
    tenant uuid NOT NULL,
    authority_epoch bigint NOT NULL CHECK (authority_epoch >= 1),
    event_sha256 text NOT NULL CHECK (event_sha256 ~ '^[0-9a-f]{64}$'),
    state text NOT NULL CHECK (state IN ('qualified', 'suspended', 'revoked'))
);

-- The review-time link does not mutate immutable plan bytes. Unknown scopes
-- conservatively match all changes for their tenant.
CREATE TABLE app.planning_plan_qualification_scopes (
    plan uuid PRIMARY KEY REFERENCES app.planning_records(id),
    tenant uuid NOT NULL,
    scope_sha256 text CHECK (scope_sha256 ~ '^[0-9a-f]{64}$')
);
CREATE INDEX planning_plan_qualification_by_scope
    ON app.planning_plan_qualification_scopes(tenant, scope_sha256);

-- A compromised runtime may not rewrite the last observed epoch, tenant,
-- or immutable event history to resurrect previously withdrawn plans.
CREATE FUNCTION app.guard_planning_qualification_head()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (
        NEW.tenant IS DISTINCT FROM OLD.tenant OR
        NEW.authority_epoch <= OLD.authority_epoch
    ) THEN
        RAISE EXCEPTION 'qualification authority epoch may only advance'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER planning_qualification_head_monotonic
    BEFORE UPDATE ON app.planning_qualification_heads
    FOR EACH ROW EXECUTE FUNCTION app.guard_planning_qualification_head();

CREATE FUNCTION app.reject_planning_qualification_inbox_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'qualification inbox is append-only' USING ERRCODE = '23514';
END;
$$;
CREATE TRIGGER planning_qualification_inbox_immutable
    BEFORE UPDATE OR DELETE ON app.planning_qualification_inbox
    FOR EACH ROW EXECUTE FUNCTION app.reject_planning_qualification_inbox_mutation();

GRANT SELECT, INSERT ON app.planning_qualification_inbox TO planning_runtime;
GRANT SELECT, INSERT, UPDATE ON app.planning_qualification_heads TO planning_runtime;
GRANT SELECT, INSERT ON app.planning_plan_qualification_scopes TO planning_runtime;
COMMIT;
