-- A physical pool ledger shared across tenants; expiry never frees live or unknown allocations.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE lifecycle_owner;
CREATE TABLE app.placement_reservations (
 id uuid PRIMARY KEY, tenant uuid NOT NULL, plan_digest text NOT NULL,
 request_digest text NOT NULL, request jsonb NOT NULL,
 state text NOT NULL CHECK (state IN ('reserved','confirmed','expired_held','released','denied')),
 expires_at bigint NOT NULL, revision bigint NOT NULL CHECK (revision > 0),
 UNIQUE(tenant,plan_digest)
);
CREATE TABLE app.placement_debits (
 reservation uuid NOT NULL REFERENCES app.placement_reservations(id),
 pool_id text NOT NULL, native_ref text NOT NULL, vector jsonb NOT NULL,
 PRIMARY KEY(reservation,pool_id)
);
CREATE TABLE app.placement_events (
 id uuid PRIMARY KEY, reservation uuid NOT NULL REFERENCES app.placement_reservations(id),
 state text NOT NULL, facts jsonb NOT NULL, occurred_at bigint NOT NULL
);
GRANT SELECT,INSERT,UPDATE ON app.placement_reservations TO lifecycle_runtime;
GRANT SELECT,INSERT ON app.placement_debits,app.placement_events TO lifecycle_runtime;
COMMIT;
