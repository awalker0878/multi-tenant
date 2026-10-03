-- Fixed guest, policy and quota executors have explicit scoped operation kinds;
-- they cannot borrow VM_POWER or DISCOVER_READ privilege for another effect.
ALTER DOMAIN hosting_controlplane.worker_operation_kind
    DROP CONSTRAINT worker_operation_kind_check;
ALTER DOMAIN hosting_controlplane.worker_operation_kind
    ADD CONSTRAINT worker_operation_kind_allowed CHECK (VALUE IN (
        'DISCOVER_READ', 'VM_CREATE', 'VM_POWER', 'DISK_ATTACH', 'NETWORK_ATTACH',
        'SNAPSHOT_CREATE', 'SNAPSHOT_EXPORT', 'SNAPSHOT_IMPORT', 'RESTORE_DATA',
        'SOURCE_FENCE', 'DESTINATION_ACTIVATE', 'DNS_CHANGE', 'IPAM_RESERVE',
        'GUEST_CONFIG', 'POLICY_APPLY', 'QUOTA_CHANGE'));
