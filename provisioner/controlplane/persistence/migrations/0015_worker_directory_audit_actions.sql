-- 0012 introduced DIRECTORY_SYNC but accidentally narrowed the action
-- allowlist created by 0007. Preserve both immutable worker identity history
-- and the signed directory marker for new and already migrated databases.
ALTER TABLE hosting_controlplane.audit_events
    DROP CONSTRAINT audit_events_action_check,
    ADD CONSTRAINT audit_events_action_check CHECK (action IN
        ('RECORD_CREATE', 'RECORD_UPDATE', 'LEASE_ACQUIRE',
         'LEASE_RENEW', 'LEASE_RELEASE', 'WORKER_CERT_ENROLL',
         'WORKER_CERT_ROTATE', 'WORKER_CERT_REVOKE', 'WORKER_REVOKE',
         'DIRECTORY_SYNC'));
