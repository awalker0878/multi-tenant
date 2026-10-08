\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE lifecycle_owner;
CREATE TABLE app.adoptions (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, actor uuid NOT NULL, command_key uuid NOT NULL,
 scope jsonb NOT NULL, fields jsonb NOT NULL, fingerprint text NOT NULL,
 state text NOT NULL CHECK (state IN ('observed','imported','managed','held','detached')),
 revision bigint NOT NULL DEFAULT 1, baseline jsonb NOT NULL, authority jsonb,
 UNIQUE(tenant,actor,command_key)
);
CREATE TABLE app.adoption_fields (
 field_key text PRIMARY KEY, adoption uuid NOT NULL REFERENCES app.adoptions(id)
);
CREATE TABLE app.expansion_events (
 sequence bigserial PRIMARY KEY, subject uuid NOT NULL, tenant uuid NOT NULL,
 actor uuid NOT NULL, kind text NOT NULL, facts jsonb NOT NULL, observed_at bigint NOT NULL
);
CREATE TABLE app.enterprise_waves (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, actor uuid NOT NULL, command_key uuid NOT NULL,
 fingerprint text NOT NULL, state text NOT NULL CHECK(state IN ('running','paused','stopped')),
 revision bigint NOT NULL DEFAULT 1, UNIQUE(tenant,actor,command_key)
);
CREATE SEQUENCE app.enterprise_dispatch_order;
CREATE TABLE app.enterprise_operations (
 id uuid PRIMARY KEY, wave uuid NOT NULL REFERENCES app.enterprise_waves(id), tenant uuid NOT NULL,
 specification jsonb NOT NULL, state text NOT NULL DEFAULT 'queued'
 CHECK(state IN ('queued','active','unknown','succeeded','failed','cancelled')),
 turn bigint NOT NULL DEFAULT 0, lease uuid, lease_until bigint,
 started_at bigint, observation jsonb
);
CREATE TABLE app.enterprise_allocations (
 operation uuid NOT NULL REFERENCES app.enterprise_operations(id), pool text NOT NULL,
 amount bigint NOT NULL CHECK(amount > 0), PRIMARY KEY(operation,pool)
);
CREATE TABLE app.expansion_commands (
 tenant uuid NOT NULL, actor uuid NOT NULL, key uuid NOT NULL, fingerprint text NOT NULL,
 result jsonb NOT NULL, PRIMARY KEY(tenant,actor,key)
);
CREATE TABLE app.enterprise_object_holds (
 object_key text PRIMARY KEY, operation uuid NOT NULL REFERENCES app.enterprise_operations(id)
);
GRANT SELECT,INSERT,UPDATE ON app.adoptions,app.enterprise_waves,app.enterprise_operations TO lifecycle_runtime;
GRANT SELECT,INSERT,DELETE ON app.adoption_fields,app.enterprise_allocations TO lifecycle_runtime;
GRANT SELECT,INSERT,DELETE ON app.enterprise_object_holds TO lifecycle_runtime;
GRANT SELECT,INSERT ON app.expansion_events,app.expansion_commands TO lifecycle_runtime;
GRANT USAGE ON SEQUENCE app.expansion_events_sequence_seq,app.enterprise_dispatch_order TO lifecycle_runtime;
COMMIT;
