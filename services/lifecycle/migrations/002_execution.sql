\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE lifecycle_owner;
CREATE TABLE app.execution_control (
 id integer PRIMARY KEY CHECK(id=1), epoch uuid NOT NULL, quarantined boolean NOT NULL DEFAULT true
);
-- Owner must establish an independently held epoch before simulation can start.
CREATE TABLE app.execution_jobs (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, actor uuid NOT NULL, command_key uuid NOT NULL,
 fingerprint text NOT NULL, plan jsonb NOT NULL, binding jsonb NOT NULL,
 approval_id uuid NOT NULL, campaign_id uuid NOT NULL, custody_epoch uuid NOT NULL,
 workflow_id text NOT NULL UNIQUE, admitted_at bigint NOT NULL,
 admission jsonb NOT NULL, UNIQUE(tenant,command_key)
);
CREATE TABLE app.execution_projection (
 job uuid PRIMARY KEY REFERENCES app.execution_jobs(id), revision bigint NOT NULL DEFAULT 1,
 state text NOT NULL DEFAULT 'admitted', reason text, updated_at bigint NOT NULL,
 cancel_requested boolean NOT NULL DEFAULT false, pause_requested boolean NOT NULL DEFAULT false,
 stop_requested boolean NOT NULL DEFAULT false, evidence jsonb,
 workflow_run_id text, workflow_version integer NOT NULL DEFAULT 1
);
CREATE TABLE app.execution_holds (
 resource_key text PRIMARY KEY, job uuid NOT NULL REFERENCES app.execution_jobs(id),
 retained boolean NOT NULL DEFAULT true
);
CREATE TABLE app.execution_dispatch (
 job uuid PRIMARY KEY REFERENCES app.execution_jobs(id), dispatched boolean NOT NULL DEFAULT false,
 run_id text, attempts integer NOT NULL DEFAULT 0
);
CREATE TABLE app.execution_operations (
 id uuid PRIMARY KEY, job uuid NOT NULL REFERENCES app.execution_jobs(id), step text NOT NULL,
 ordinal integer NOT NULL, outcome text NOT NULL DEFAULT 'not_started'
 CHECK(outcome IN ('not_started','attempting','outcome_unknown','confirmed_failed','confirmed_succeeded')),
 attempt_id uuid, grant_id uuid, worker text, epoch uuid, expires_at bigint,
 redeemed boolean NOT NULL DEFAULT false, observation jsonb, revision bigint NOT NULL DEFAULT 1,
 UNIQUE(job,step), UNIQUE(job,ordinal), UNIQUE(grant_id)
);
CREATE TABLE app.execution_events (
 id uuid PRIMARY KEY, job uuid NOT NULL REFERENCES app.execution_jobs(id),
 kind text NOT NULL, facts jsonb NOT NULL, occurred_at bigint NOT NULL
);
CREATE TABLE app.execution_commands (
 tenant uuid NOT NULL, command_key uuid NOT NULL, fingerprint text NOT NULL,
 job uuid NOT NULL REFERENCES app.execution_jobs(id), receipt jsonb NOT NULL,
 PRIMARY KEY(tenant,command_key)
);
CREATE TABLE app.execution_alerts (
 id uuid PRIMARY KEY, job uuid NOT NULL REFERENCES app.execution_jobs(id),
 projection_revision bigint NOT NULL, payload jsonb NOT NULL, receipt text,
 UNIQUE(job,projection_revision)
);
GRANT SELECT ON app.execution_control TO lifecycle_runtime;
GRANT SELECT,INSERT ON app.execution_jobs,app.execution_events,app.execution_commands TO lifecycle_runtime;
GRANT SELECT,INSERT,UPDATE ON app.execution_projection,app.execution_holds,app.execution_dispatch,
 app.execution_operations,app.execution_alerts TO lifecycle_runtime;
COMMIT;
