-- Pre-tenant OIDC directory. Only a dedicated resolver role may SELECT; only
-- an IAM sync writer may mutate. Neither credential is exposed to HTTP callers.
-- The resolver must find the tenant *before* tenant RLS context can be set.
CREATE TABLE hosting_controlplane.directory_subjects (
    issuer text NOT NULL,
    subject text NOT NULL,
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    identity_kind text NOT NULL CHECK (identity_kind IN ('HUMAN', 'WORKER')),
    active boolean NOT NULL,
    grants jsonb NOT NULL CHECK (jsonb_typeof(grants) = 'array'),
    generation bigint NOT NULL CHECK (generation > 0),
    signed_digest text NOT NULL CHECK (signed_digest ~ '^[0-9a-f]{64}$'),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (issuer, subject)
);

CREATE TABLE hosting_controlplane.directory_sessions (
    issuer text NOT NULL,
    subject text NOT NULL,
    session_id text NOT NULL,
    expires_at timestamptz NOT NULL,
    PRIMARY KEY (issuer, subject, session_id),
    FOREIGN KEY (issuer, subject) REFERENCES hosting_controlplane.directory_subjects
        (issuer, subject) ON DELETE CASCADE
);

CREATE TABLE hosting_controlplane.directory_sync_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    issuer text NOT NULL,
    subject text NOT NULL,
    generation bigint NOT NULL CHECK (generation > 0),
    signed_digest text NOT NULL CHECK (signed_digest ~ '^[0-9a-f]{64}$'),
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (issuer, subject, generation)
);
CREATE TRIGGER directory_sync_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.directory_sync_events
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

-- Directory membership is looked up with a restricted global resolver
-- credential. This is intentionally outside tenant RLS: the tenant is unknown
-- until the lookup succeeds. Never grant direct SQL or table privileges to an
-- end user, API runtime, worker runtime, or an arbitrary tenant credential.
