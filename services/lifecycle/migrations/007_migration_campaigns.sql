\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE lifecycle_owner;
CREATE TABLE app.migration_campaigns (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, actor uuid NOT NULL,
 scope jsonb NOT NULL, settings jsonb NOT NULL, fingerprint text NOT NULL,
 state text NOT NULL CHECK(state IN ('draft','scheduled','paused','cancelled','complete')),
 revision bigint NOT NULL DEFAULT 1, created_at bigint NOT NULL,
 last_started_at bigint, UNIQUE(id,tenant)
);
CREATE TABLE app.migration_members (
 id uuid PRIMARY KEY, campaign uuid NOT NULL REFERENCES app.migration_campaigns(id),
 tenant uuid NOT NULL, ordinal integer NOT NULL, specification jsonb NOT NULL,
 job uuid UNIQUE REFERENCES app.native_jobs(id),
 state text NOT NULL DEFAULT 'queued' CHECK(state IN ('queued','admitted','complete','held','cancelled')),
 reason text, started_at bigint, completed_at bigint,
 FOREIGN KEY(campaign,tenant) REFERENCES app.migration_campaigns(id,tenant),
 UNIQUE(campaign,ordinal)
);
CREATE TABLE app.migration_campaign_commands (
 tenant uuid NOT NULL, actor uuid NOT NULL, command_key uuid NOT NULL,
 fingerprint text NOT NULL, result jsonb NOT NULL,
 PRIMARY KEY(tenant,actor,command_key)
);
CREATE TABLE app.migration_campaign_events (
 id uuid PRIMARY KEY, campaign uuid NOT NULL REFERENCES app.migration_campaigns(id),
 actor uuid NOT NULL, kind text NOT NULL, facts jsonb NOT NULL, occurred_at bigint NOT NULL
);
CREATE TABLE app.migration_pool_observations (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, pool_key text NOT NULL,
 capacity bigint NOT NULL CHECK(capacity>=0), paused boolean NOT NULL,
 observed_at bigint NOT NULL, expires_at bigint NOT NULL,
 evidence_sha256 text NOT NULL, observer uuid NOT NULL
);
CREATE INDEX migration_pool_current ON app.migration_pool_observations(pool_key,observed_at DESC);
CREATE TABLE app.migration_allocations (
 member uuid NOT NULL REFERENCES app.migration_members(id), pool_key text NOT NULL,
 amount bigint NOT NULL CHECK(amount>0), acquired_at bigint NOT NULL,
 PRIMARY KEY(member,pool_key)
);
CREATE TABLE app.migration_allocation_releases (
 member uuid NOT NULL, pool_key text NOT NULL, evidence_sha256 text NOT NULL,
 released_at bigint NOT NULL,
 PRIMARY KEY(member,pool_key),
 FOREIGN KEY(member,pool_key) REFERENCES app.migration_allocations(member,pool_key)
);
CREATE TABLE app.migration_stage_slots (
 operation uuid PRIMARY KEY REFERENCES app.native_operations(id),
 member uuid NOT NULL REFERENCES app.migration_members(id), phase text NOT NULL,
 acquired_at bigint NOT NULL
);
CREATE TABLE app.migration_stage_releases (
 operation uuid PRIMARY KEY REFERENCES app.migration_stage_slots(operation),
 released_at bigint NOT NULL
);
CREATE TABLE app.migration_performance_samples (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, route_sha256 text NOT NULL,
 worker uuid NOT NULL, sample jsonb NOT NULL, observed_at bigint NOT NULL,
 fingerprint text NOT NULL
);
CREATE INDEX migration_samples_route ON app.migration_performance_samples(tenant,route_sha256,observed_at DESC);
GRANT SELECT,INSERT,UPDATE ON app.migration_campaigns,app.migration_members TO lifecycle_runtime;
GRANT SELECT,INSERT ON app.migration_campaign_commands,app.migration_campaign_events,
 app.migration_pool_observations,app.migration_allocations,app.migration_allocation_releases,
 app.migration_stage_slots,app.migration_stage_releases,app.migration_performance_samples TO lifecycle_runtime;
COMMIT;
