\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE simulation_owner;
CREATE SCHEMA sim AUTHORIZATION simulation_owner;
CREATE TABLE sim.observations (
 operation_id uuid NOT NULL, attempt_id uuid NOT NULL, binding jsonb NOT NULL,
 effect_count integer NOT NULL CHECK(effect_count IN(0,1)), accepted_at bigint,
 PRIMARY KEY(operation_id,attempt_id)
);
CREATE UNIQUE INDEX one_logical_effect ON sim.observations(operation_id) WHERE effect_count=1;
CREATE TABLE sim.writers (
 job uuid PRIMARY KEY, source_writer boolean NOT NULL, target_writer boolean NOT NULL,
 CHECK(NOT(source_writer AND target_writer))
);
GRANT USAGE ON SCHEMA sim TO simulation_runtime;
GRANT SELECT,INSERT ON sim.observations TO simulation_runtime;
GRANT SELECT,INSERT,UPDATE ON sim.writers TO simulation_runtime;
COMMIT;
