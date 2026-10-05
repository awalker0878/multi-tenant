-- Installation events share the immutable event-ID namespace, with no tenant projection.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE console_owner;
ALTER TABLE app.notification_inbox ALTER COLUMN tenant_id DROP NOT NULL;
CREATE TABLE IF NOT EXISTS app.installation_notification_hint (
    id smallint PRIMARY KEY CHECK (id = 1),
    cursor uuid NOT NULL,
    updated_at timestamptz NOT NULL
);
REVOKE ALL ON app.installation_notification_hint FROM console_runtime;
GRANT SELECT, INSERT, UPDATE ON app.installation_notification_hint TO console_runtime;
COMMIT;
