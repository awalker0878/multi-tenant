-- Application-owned migration flow choices; never store native rule definitions.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE planning_owner;
CREATE TABLE app.planning_application_flow_reviews (
    tenant uuid NOT NULL, actor uuid NOT NULL, application uuid NOT NULL,
    environment uuid NOT NULL, site uuid NOT NULL,
    revision integer NOT NULL CHECK (revision > 0),
    context_sha256 text NOT NULL CHECK (context_sha256 ~ '^[a-f0-9]{64}$'),
    payload jsonb NOT NULL,
    updated_at bigint NOT NULL,
    PRIMARY KEY (tenant, actor, application, environment, site)
);
GRANT SELECT, INSERT, UPDATE ON app.planning_application_flow_reviews TO planning_runtime;
COMMIT;
