\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE lifecycle_owner;
-- Only new, atomically admitted jobs enter dispatch. Historical jobs are not requeued.
CREATE TABLE app.native_dispatch (
 job uuid PRIMARY KEY REFERENCES app.native_jobs(id),
 workflow_id text NOT NULL UNIQUE CHECK(workflow_id='p07-native-v1-'||job::text),
 dispatched boolean NOT NULL DEFAULT false, attempts bigint NOT NULL DEFAULT 0 CHECK(attempts>=0),
 run_id text
);
GRANT SELECT,INSERT ON app.native_dispatch TO lifecycle_runtime;
GRANT UPDATE(dispatched,attempts,run_id) ON app.native_dispatch TO lifecycle_runtime;
COMMIT;
