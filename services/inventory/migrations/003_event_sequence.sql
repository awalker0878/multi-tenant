-- Apply as inventory_owner after 002_inventory.sql. Existing facts keep their bytes.
BEGIN;
ALTER TABLE inventory.outbox ADD COLUMN IF NOT EXISTS sequence bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNIQUE INDEX IF NOT EXISTS inventory_event_sequence ON inventory.outbox(sequence);
GRANT USAGE ON SEQUENCE inventory.outbox_sequence_seq TO inventory_runtime;
COMMIT;
