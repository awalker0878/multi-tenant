-- Apply as inventory_owner, never the runtime role. Additive and replayable.
BEGIN;
CREATE SCHEMA IF NOT EXISTS inventory;
CREATE TABLE IF NOT EXISTS inventory.endpoints (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, site uuid NOT NULL, owner_id uuid NOT NULL,
 policy_id uuid NOT NULL, policy_digest text NOT NULL, epoch uuid NOT NULL,
 worker_id uuid NOT NULL, platform text NOT NULL, native_scope text NOT NULL,
 label text NOT NULL, revision integer NOT NULL, revoked boolean NOT NULL DEFAULT false,
 created_at double precision NOT NULL, current_generation uuid,
 UNIQUE (tenant, policy_id)
);
CREATE INDEX IF NOT EXISTS endpoints_scope ON inventory.endpoints(tenant, site, id);
CREATE TABLE IF NOT EXISTS inventory.commands (
 tenant uuid NOT NULL, actor uuid NOT NULL, command_key uuid NOT NULL,
 digest text NOT NULL, result jsonb NOT NULL, PRIMARY KEY(tenant,actor,command_key)
);
CREATE TABLE IF NOT EXISTS inventory.jobs (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, endpoint uuid NOT NULL REFERENCES inventory.endpoints(id),
 policy_digest text NOT NULL, endpoint_revision integer NOT NULL,
 status text NOT NULL, created_at double precision NOT NULL, updated_at double precision NOT NULL,
 next_at double precision NOT NULL, lease_token uuid, lease_until double precision,
 worker_id uuid, failures integer NOT NULL DEFAULT 0, page_count integer NOT NULL DEFAULT 0,
 stream integer NOT NULL DEFAULT 0, cursor text, reason text, completed_at double precision
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_discovery ON inventory.jobs(endpoint)
 WHERE status IN ('queued','running');
CREATE INDEX IF NOT EXISTS jobs_queue ON inventory.jobs(status,next_at,created_at);
CREATE INDEX IF NOT EXISTS jobs_tenant ON inventory.jobs(tenant,endpoint,created_at DESC);
CREATE TABLE IF NOT EXISTS inventory.pages (
 job uuid NOT NULL REFERENCES inventory.jobs(id), sequence integer NOT NULL,
 lease_token uuid NOT NULL UNIQUE, digest text NOT NULL, payload jsonb NOT NULL,
 collected_at double precision NOT NULL, PRIMARY KEY(job,sequence)
);
CREATE TABLE IF NOT EXISTS inventory.resources (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, endpoint uuid NOT NULL REFERENCES inventory.endpoints(id),
 kind text NOT NULL, native_id text NOT NULL, incarnation text,
 last_generation uuid NOT NULL, tombstone boolean NOT NULL DEFAULT false,
 identity_hold boolean NOT NULL DEFAULT false, absent_count integer NOT NULL DEFAULT 0,
 UNIQUE(endpoint,kind,native_id)
);
CREATE INDEX IF NOT EXISTS resources_tenant ON inventory.resources(tenant,endpoint,id);
CREATE TABLE IF NOT EXISTS inventory.observations (
 generation uuid NOT NULL REFERENCES inventory.jobs(id), resource uuid NOT NULL REFERENCES inventory.resources(id),
 tenant uuid NOT NULL, payload jsonb NOT NULL, collected_at double precision NOT NULL,
 expires_at double precision NOT NULL, PRIMARY KEY(generation,resource)
);
CREATE INDEX IF NOT EXISTS observation_tenant ON inventory.observations(tenant,generation,resource);
CREATE TABLE IF NOT EXISTS inventory.matches (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, resource uuid NOT NULL REFERENCES inventory.resources(id),
 application uuid NOT NULL, revision uuid NOT NULL, generation uuid NOT NULL,
 actor uuid NOT NULL, created_at double precision NOT NULL,
 UNIQUE(tenant,resource,application,revision,generation)
);
CREATE TABLE IF NOT EXISTS inventory.audit (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, actor text NOT NULL, operation text NOT NULL,
 resource uuid NOT NULL, at double precision NOT NULL, details jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS inventory.outbox (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, aggregate uuid NOT NULL,
 event_type text NOT NULL, at double precision NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS inventory.delivery (
 event uuid PRIMARY KEY REFERENCES inventory.outbox(id), delivered_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS inventory.budgets (
 authority text PRIMARY KEY, next_at double precision NOT NULL, last_tenant uuid,
 dispatched bigint NOT NULL DEFAULT 0, throttled bigint NOT NULL DEFAULT 0
);
REVOKE ALL ON SCHEMA inventory FROM PUBLIC;
GRANT USAGE ON SCHEMA inventory TO inventory_runtime;
GRANT SELECT,INSERT,UPDATE ON inventory.endpoints,inventory.jobs,inventory.resources,inventory.budgets TO inventory_runtime;
GRANT SELECT,INSERT ON inventory.commands,inventory.pages,inventory.observations,inventory.matches,
 inventory.audit,inventory.outbox,inventory.delivery TO inventory_runtime;
COMMIT;
