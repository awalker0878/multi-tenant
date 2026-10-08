-- P09-A capture, conversion, import and durable continuation events.
-- Preserve every prior attempt and receipt; runtime permissions remain append-only.
ALTER TABLE native.events DROP CONSTRAINT events_kind_check;
ALTER TABLE native.events ADD CONSTRAINT events_kind_check CHECK (kind IN (
 'prepared', 'request_started', 'request_accepted', 'poll_observed', 'outcome_unknown',
 'readback', 'export_lease', 'disk_transferred', 'export_complete',
 'vmware_request_started', 'vmware_task_accepted', 'vmware_task_observed', 'snapshot_bound',
 'clone_bound', 'ovf_retained', 'conversion_started', 'conversion_observed', 'transfer_progress',
 'conversion_complete', 'ahv_task_accepted', 'source_request_started', 'source_object_created',
 'source_capture_bound', 'transfer_started', 'transfer_continued', 'continuation_held',
 'guest_copy_prepared', 'import_lease'
));
