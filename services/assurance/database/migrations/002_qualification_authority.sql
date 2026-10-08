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
GRANT SELECT, INSERT, UPDATE (delivered_at) ON app.qualification_authority_outbox
    TO assurance_runtime;
COMMIT;
