-- P08 extends the certainty journal without deleting prior attempts/custody.
ALTER TABLE native.events DROP CONSTRAINT events_kind_check;
ALTER TABLE native.events ADD CONSTRAINT events_kind_check CHECK (kind IN (
 'prepared', 'request_started', 'request_accepted', 'poll_observed', 'outcome_unknown',
 'readback', 'export_lease', 'disk_transferred', 'export_complete',
 'vmware_request_started', 'vmware_task_accepted', 'vmware_task_observed', 'snapshot_bound',
 'clone_bound', 'ovf_retained', 'conversion_started', 'conversion_observed', 'transfer_progress'
));
CREATE TABLE native.custody_generations (
 custody_id uuid NOT NULL, generation bigint NOT NULL CHECK(generation>=0),
 job_id uuid NOT NULL, scope jsonb NOT NULL, PRIMARY KEY(custody_id,generation)
);
INSERT INTO native.custody_generations
 SELECT h.custody_id, (a.binding->>'custody_generation')::bigint,
        (a.binding->>'job_id')::uuid,
        jsonb_build_object('tenant_id',a.binding->'tenant_id','site_id',a.binding->'site_id',
          'project_id',a.binding->'project_id','resource_id',a.binding->'resource_id',
          'ownership_digest',a.binding->'ownership_digest')
 FROM native.custody_holds h JOIN native.attempts a ON a.operation_id=h.operation_id;
REVOKE ALL ON native.custody_generations FROM PUBLIC;
GRANT SELECT,INSERT ON native.custody_generations TO native_runtime;
