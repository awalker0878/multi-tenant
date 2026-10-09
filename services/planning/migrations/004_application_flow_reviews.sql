-- Application/migration-owned flow choices with explicit approving reviewer.
-- Native evidence is NOT stored here as durable proof.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE planning_owner;
CREATE TABLE app.planning_application_flow_reviews (
    tenant uuid NOT NULL, application uuid NOT NULL,
    environment uuid NOT NULL, site uuid NOT NULL, assessment_id uuid NOT NULL,
    reviewed_by_actor uuid NOT NULL, revision integer NOT NULL CHECK (revision > 0),
    context_sha256 text NOT NULL CHECK (context_sha256 ~ '^[a-f0-9]{64}$'),
    payload jsonb NOT NULL, updated_at bigint NOT NULL,
    PRIMARY KEY (tenant, application, environment, site, assessment_id)
);
CREATE INDEX planning_application_flow_latest ON app.planning_application_flow_reviews
    (tenant, application, environment, site, updated_at);
GRANT SELECT, INSERT, UPDATE ON app.planning_application_flow_reviews TO planning_runtime;
COMMIT;
