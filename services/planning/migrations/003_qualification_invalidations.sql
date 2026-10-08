-- P05/CT-02: a tenant-scoped durable inbox for Assurance invalidation hints.
-- These rows never confer native support; direct Assurance reads remain authoritative.
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
    state text NOT NULL CHECK (state IN ('qualified','suspended','revoked')),
    received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (scope_sha256, authority_epoch)
);

CREATE TABLE app.planning_qualification_heads (
    scope_sha256 text PRIMARY KEY CHECK (scope_sha256 ~ '^[0-9a-f]{64}$'),
    tenant uuid NOT NULL,
    authority_epoch bigint NOT NULL CHECK (authority_epoch >= 1),
    event_sha256 text NOT NULL CHECK (event_sha256 ~ '^[0-9a-f]{64}$'),
    state text NOT NULL CHECK (state IN ('qualified','suspended','revoked'))
);

-- Immutable inbox; the runtime can only advance the per-scope head.
CREATE FUNCTION app.guard_planning_qualification_head()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (
        NEW.tenant <> OLD.tenant OR
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

GRANT SELECT, INSERT ON app.planning_qualification_inbox TO planning_runtime;
GRANT SELECT, INSERT, UPDATE ON app.planning_qualification_heads TO planning_runtime;
COMMIT;
