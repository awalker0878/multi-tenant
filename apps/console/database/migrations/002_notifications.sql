-- Console-owned invalidation hints. No Governance data or permissions are projected.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE console_owner;
CREATE TABLE IF NOT EXISTS app.notification_inbox (
    event_id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    event_type varchar(64) NOT NULL,
    wire_sha256 char(64) NOT NULL,
    received_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.notification_hints (
    tenant_id uuid PRIMARY KEY,
    cursor uuid NOT NULL,
    updated_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.notification_quarantine (
    envelope_sha256 char(64) PRIMARY KEY,
    reason varchar(32) NOT NULL,
    envelope_ciphertext text NOT NULL,
    received_at timestamptz NOT NULL
);
-- Revoke broad provisioning defaults as well as previous grants on rerun.
REVOKE ALL ON app.notification_inbox,app.notification_hints,app.notification_quarantine FROM console_runtime;
GRANT SELECT,INSERT ON app.notification_inbox,app.notification_quarantine TO console_runtime;
GRANT SELECT,INSERT,UPDATE ON app.notification_hints TO console_runtime;
COMMIT;
