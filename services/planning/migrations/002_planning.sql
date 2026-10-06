-- P05 immutable assessments, compiled semantic bytes, approval bindings and fact inbox.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE planning_owner;
CREATE TABLE app.planning_records (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, actor uuid NOT NULL, application uuid NOT NULL,
 environment uuid NOT NULL, kind text NOT NULL CHECK (kind IN ('assessment','plan')),
 payload jsonb NOT NULL, digest text NOT NULL, created_at bigint NOT NULL
);
CREATE INDEX planning_records_scope ON app.planning_records(tenant,application,environment,kind,id);
CREATE TABLE app.planning_commands (
 tenant uuid NOT NULL, actor uuid NOT NULL, command_key uuid NOT NULL,
 fingerprint text NOT NULL, response jsonb NOT NULL, created_at bigint NOT NULL,
 PRIMARY KEY(tenant,actor,command_key)
);
CREATE TABLE app.planning_outbox (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, payload jsonb NOT NULL,
 sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE
);
CREATE TABLE app.planning_deliveries (id uuid PRIMARY KEY REFERENCES app.planning_outbox(id));
CREATE TABLE app.planning_fact_inbox (event_id uuid PRIMARY KEY,tenant uuid NOT NULL,digest text NOT NULL,envelope jsonb NOT NULL);
CREATE TABLE app.planning_invalidations (tenant uuid NOT NULL, plan uuid NOT NULL REFERENCES app.planning_records(id),event_id uuid NOT NULL REFERENCES app.planning_fact_inbox(event_id),PRIMARY KEY(plan,event_id));
CREATE TABLE app.planning_fact_rejections (id uuid PRIMARY KEY,owner text NOT NULL,payload_digest text NOT NULL);
GRANT SELECT,INSERT ON app.planning_fact_rejections TO planning_runtime;
GRANT SELECT,INSERT ON app.planning_records,app.planning_commands,app.planning_outbox,app.planning_deliveries,app.planning_fact_inbox,app.planning_invalidations TO planning_runtime;
GRANT USAGE,SELECT ON SEQUENCE app.planning_outbox_sequence_seq TO planning_runtime;
COMMIT;
