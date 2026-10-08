\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE lifecycle_owner;
ALTER TABLE app.execution_events ADD COLUMN sequence bigint GENERATED ALWAYS AS IDENTITY;
GRANT USAGE ON SEQUENCE app.execution_events_sequence_seq TO lifecycle_runtime;
COMMIT;
