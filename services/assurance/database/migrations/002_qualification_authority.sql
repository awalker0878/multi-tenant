\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE assurance_owner;

CREATE TABLE app.qualification_authority_heads (
    scope_sha256 text PRIMARY KEY CHECK (scope_sha256 ~ '^[0-9a-f]{64}$'),
    tenant uuid NOT NULL,
    authority_epoch bigint NOT NULL CHECK (authority_epoch >= 1),
    state text NOT NULL CHECK (state IN ('qualified', 'suspended', 'revoked')),
    decision_sha256 text CHECK (decision_sha256 ~ '^[0-9a-f]{64}$'),
    decision_revision bigint NOT NULL CHECK (decision_revision >= 0),
    reviewer_id text NOT NULL,
    bundle jsonb NOT NULL,
    last_event_sha256 text NOT NULL CHECK (last_event_sha256 ~ '^[0-9a-f]{64}$'),
    updated_at bigint NOT NULL
);

CREATE TABLE app.qualification_authority_events (
    event_id uuid PRIMARY KEY,
    command_id uuid NOT NULL,
    scope_sha256 text NOT NULL REFERENCES app.qualification_authority_heads(scope_sha256),
    tenant uuid NOT NULL,
    authority_epoch bigint NOT NULL CHECK (authority_epoch >= 1),
    operation text NOT NULL CHECK (operation IN ('publish', 'suspend', 'revoke', 'restore')),
    request_sha256 text NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
    previous_event_sha256 text CHECK (previous_event_sha256 ~ '^[0-9a-f]{64}$'),
    event_sha256 text NOT NULL CHECK (event_sha256 ~ '^[0-9a-f]{64}$'),
    result jsonb NOT NULL,
    recorded_at bigint NOT NULL,
    UNIQUE (scope_sha256, command_id),
    UNIQUE (scope_sha256, authority_epoch)
);

CREATE TABLE app.qualification_authority_outbox (
    event_id uuid PRIMARY KEY REFERENCES app.qualification_authority_events(event_id),
    scope_sha256 text NOT NULL,
    authority_epoch bigint NOT NULL,
    payload jsonb NOT NULL,
    created_at bigint NOT NULL,
    delivered_at bigint
);

-- A runtime writer cannot roll the publication head backwards or skip an epoch.
CREATE FUNCTION app.guard_qualification_head_epoch()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.authority_epoch <> 1 THEN
        RAISE EXCEPTION 'initial qualification epoch must be one' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' AND NEW.authority_epoch <> OLD.authority_epoch + 1 THEN
        RAISE EXCEPTION 'qualification authority epoch must increase exactly once'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER qualification_head_monotonic
    BEFORE INSERT OR UPDATE ON app.qualification_authority_heads
    FOR EACH ROW EXECUTE FUNCTION app.guard_qualification_head_epoch();

CREATE FUNCTION app.verify_qualification_head_event()
RETURNS trigger LANGUAGE plpgsql AS $
DECLARE
    prior_event text;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        prior_event := OLD.last_event_sha256;
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM app.qualification_authority_events e
          JOIN app.qualification_authority_outbox o ON o.event_id = e.event_id
         WHERE e.scope_sha256 = NEW.scope_sha256
           AND e.tenant = NEW.tenant
           AND e.authority_epoch = NEW.authority_epoch
           AND e.event_sha256 = NEW.last_event_sha256
           AND e.recorded_at = NEW.updated_at
           AND (e.result->>'state') = NEW.state
           AND (e.result->>'authority_epoch')::bigint = NEW.authority_epoch
           AND (e.result->>'decision_sha256') IS NOT DISTINCT FROM NEW.decision_sha256
           AND (e.result->>'decision_revision')::bigint = NEW.decision_revision
           AND (e.result->>'reviewer_id') = NEW.reviewer_id
           AND e.result->'bundle' = NEW.bundle
           AND o.scope_sha256 = NEW.scope_sha256
           AND o.authority_epoch = NEW.authority_epoch
           AND o.payload->>'event_sha256' = e.event_sha256
           AND o.payload->>'tenant_id' = NEW.tenant::text
           AND e.previous_event_sha256 IS NOT DISTINCT FROM prior_event
    ) THEN
        RAISE EXCEPTION 'qualification head, history, and outbox disagree'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE CONSTRAINT TRIGGER qualification_head_requires_event
    AFTER INSERT OR UPDATE ON app.qualification_authority_heads
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION app.verify_qualification_head_event();

CREATE FUNCTION app.reject_qualification_head_delete()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'qualification history head cannot be deleted' USING ERRCODE = '23514';
END;
$$;
CREATE TRIGGER qualification_head_undeletable
    BEFORE DELETE ON app.qualification_authority_heads
    FOR EACH ROW EXECUTE FUNCTION app.reject_qualification_head_delete();

CREATE FUNCTION app.reject_qualification_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'qualification history is append-only' USING ERRCODE = '23514';
END;
$$;
CREATE TRIGGER qualification_history_append_only
    BEFORE UPDATE OR DELETE ON app.qualification_authority_events
    FOR EACH ROW EXECUTE FUNCTION app.reject_qualification_history_mutation();

REVOKE ALL ON app.qualification_authority_heads,
    app.qualification_authority_events, app.qualification_authority_outbox
    FROM assurance_runtime;
GRANT SELECT, INSERT, UPDATE ON app.qualification_authority_heads TO assurance_runtime;
GRANT SELECT, INSERT ON app.qualification_authority_events TO assurance_runtime;
GRANT SELECT, INSERT ON app.qualification_authority_outbox TO assurance_runtime;
GRANT UPDATE (delivered_at) ON app.qualification_authority_outbox TO assurance_runtime;
COMMIT;
