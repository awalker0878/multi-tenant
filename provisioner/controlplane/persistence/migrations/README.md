# PostgreSQL control-plane migrations

Install the `controlplane` extra, provision a dedicated migration role and a
separate runtime role, then run `python -m
provisioner.controlplane.persistence.migrate` with libpq connection settings
for the migration role. The runner applies packaged `0001_*.sql`, `0002_*.sql`,
and later migrations in filename order, each in its own transaction under a
session advisory lock. Applied SQL
is checksummed; modified or missing history stops startup.

The runtime role must be `NOSUPERUSER NOBYPASSRLS`, must not own the tables or
schema, must not inherit the migration role, and must not have `CREATE`,
`DELETE`, or `TRUNCATE` on product tables. The migration role grants only the
required permissions after migrations:

```sql
GRANT USAGE ON SCHEMA hosting_controlplane TO hosting_runtime;
GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.enterprise_records
    TO hosting_runtime;
GRANT SELECT, INSERT ON hosting_controlplane.enterprise_record_history
    TO hosting_runtime;
GRANT SELECT, INSERT ON hosting_controlplane.audit_events TO hosting_runtime;
GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.native_ownership
    TO hosting_runtime;
GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.operation_jobs,
    hosting_controlplane.job_outbox TO hosting_runtime;
GRANT SELECT, INSERT ON hosting_controlplane.job_events TO hosting_runtime;
GRANT SELECT ON hosting_controlplane.plan_authority_state,
    hosting_controlplane.plan_approvals,
    hosting_controlplane.plan_revocations TO hosting_runtime;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA hosting_controlplane
    TO hosting_runtime;
-- Provision a separate authority writer for approval and revocation DML.
```

The service sets `app.organization_id` and `app.tenant_id` with transaction-local
`set_config(..., true)` after checking its authenticated principal. The runtime
role must have no arbitrary SQL endpoint: PostgreSQL custom settings can be
changed by a role able to issue SQL. Composite tenant keys and forced RLS
provide defense in depth; authentication and authorization remain mandatory.

The audit/history trigger forbids UPDATE and DELETE, and the restricted runtime
role cannot TRUNCATE or change the trigger. Database administrators and backup
operators still have privileged access. Independent signed checkpoints and
external evidence retention are delivered by B13. Back up the entire database,
including `schema_migrations`, `enterprise_record_history`, `audit_events`,
and ownership lease epochs. A restored site remains observation-only until it
reconciles native ownership and stale epochs (B44).

Owner leases fence cooperative workers; they do not fence a guest, hypervisor,
storage writer, or external administrator. An expired lease remains held and
cannot be automatically reacquired. Recovery requires an independently reviewed
reconciliation operation in B11. A lease expiry alone cannot authorize another
production writer. The route must separately prove native exclusion.
