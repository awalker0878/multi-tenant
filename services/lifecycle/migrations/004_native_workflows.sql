\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE lifecycle_owner;
-- Deliberately empty: only the custody owner can install an independently held epoch.
CREATE TABLE app.native_control (
 id integer PRIMARY KEY CHECK(id=1), epoch uuid NOT NULL, quarantined boolean NOT NULL DEFAULT true
);
CREATE TABLE app.native_jobs (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, command_key uuid NOT NULL,
 fingerprint text NOT NULL, plan jsonb NOT NULL, created_at bigint NOT NULL,
 UNIQUE(tenant,command_key)
);
CREATE TABLE app.native_projection (
 job uuid PRIMARY KEY REFERENCES app.native_jobs(id), revision bigint NOT NULL DEFAULT 1,
 state text NOT NULL CHECK(state IN ('prepared','running','held','active','retired','stopped')),
 stopped boolean NOT NULL DEFAULT false, reason text, updated_at bigint NOT NULL
);
CREATE TABLE app.native_resource_holds (
 resource_key text PRIMARY KEY, custody_id uuid NOT NULL UNIQUE,
 job uuid NOT NULL REFERENCES app.native_jobs(id)
);
CREATE TABLE app.native_operations (
 id uuid PRIMARY KEY, job uuid NOT NULL REFERENCES app.native_jobs(id),
 stage text NOT NULL, binding jsonb NOT NULL, fingerprint text NOT NULL,
 created_at bigint NOT NULL, UNIQUE(job,stage)
);
CREATE TABLE app.native_redemptions (
 operation uuid PRIMARY KEY REFERENCES app.native_operations(id),
 worker uuid NOT NULL, redeemed_at bigint NOT NULL
);
CREATE TABLE app.native_observations (
 operation uuid PRIMARY KEY REFERENCES app.native_operations(id),
 digest text NOT NULL, records jsonb NOT NULL, observed_at bigint NOT NULL
);
CREATE TABLE app.native_events (
 sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 job uuid NOT NULL REFERENCES app.native_jobs(id), kind text NOT NULL,
 facts jsonb NOT NULL CHECK(octet_length(facts::text)<=262144), occurred_at bigint NOT NULL
);
GRANT SELECT ON app.native_control TO lifecycle_runtime;
GRANT SELECT,INSERT ON app.native_jobs,app.native_operations,app.native_redemptions,
 app.native_observations,app.native_events TO lifecycle_runtime;
GRANT USAGE,SELECT ON SEQUENCE app.native_events_sequence_seq TO lifecycle_runtime;
GRANT SELECT,INSERT,UPDATE ON app.native_projection,app.native_resource_holds TO lifecycle_runtime;
COMMIT;
