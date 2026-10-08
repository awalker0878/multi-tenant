BEGIN;
SET ROLE pd_owner;
GRANT USAGE ON SCHEMA app TO pd_runtime,pd_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA app TO pd_runtime,pd_backup;
GRANT INSERT ON app.permits,app.attachments TO pd_runtime;
COMMIT;
