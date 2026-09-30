# PostgreSQL control-plane migrations

Install the `controlplane` extra, provision a dedicated `NOSUPERUSER
NOBYPASSRLS` migration role with `CREATE` on the database and a separate
runtime role, then run `python -m
provisioner.controlplane.persistence.migrate` with libpq connection settings
for the migration role. The runner applies packaged migrations `0001`–`0021`
in filename order, each in its own transaction under a
session advisory lock. Applied SQL
is checksummed; modified or missing history stops startup.

The migration role owns the schema, tables, triggers, and SECURITY DEFINER
functions. It must not be a superuser or have BYPASSRLS; FORCE RLS must still
apply inside the authority lock function. The runtime role must be `NOSUPERUSER
NOBYPASSRLS`, must not own the tables or
schema, must not inherit the migration role, and must not have `CREATE`,
`DELETE`, or `TRUNCATE` on product tables. The migration role grants only the
required permissions after migrations:

```sql
GRANT USAGE ON SCHEMA hosting_controlplane TO hosting_runtime;
GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.enterprise_records
    TO hosting_runtime;
GRANT SELECT, INSERT ON hosting_controlplane.environment_registrations
    TO hosting_runtime;
GRANT SELECT ON hosting_controlplane.discovery_campaigns,
    hosting_controlplane.discovery_generations,
    hosting_controlplane.discovery_observations,
    hosting_controlplane.discovery_absence_candidates TO hosting_runtime;
GRANT SELECT, INSERT ON hosting_controlplane.application_draft_revisions
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
GRANT EXECUTE ON FUNCTION
    hosting_controlplane.lock_authority_scope(text, text, text)
    TO hosting_runtime;
GRANT EXECUTE ON FUNCTION
    hosting_controlplane.lock_native_worker_scope(text, text, text)
    TO hosting_runtime;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA hosting_controlplane
    TO hosting_runtime;
-- Provision a separate authority writer for approval and revocation DML.
-- Grant EXECUTE on lock_authority_scope to that writer as well, plus only the
-- exact authority-table DML it needs. No UPDATE on append-only approvals.
```

The service sets `app.organization_id` and `app.tenant_id` with transaction-local
`set_config(..., true)` after checking its authenticated principal. The runtime
role must have no arbitrary SQL endpoint: PostgreSQL custom settings can be
changed by a role able to issue SQL. Composite tenant keys and forced RLS
provide defense in depth; authentication and authorization remain mandatory.
Migration `0013` stores append-only human environment declarations under forced
tenant RLS. Its generated status is always `DECLARED_UNVERIFIED`. The API checks
the exact native site, WSD, endpoint, scope and platform grant before insertion
or returning a row; this registry grants no native access or execution authority.

OIDC enrollment uses a separate pre-tenant directory boundary (0009). The
OIDC access token supplies only issuer, subject, and session ID; it cannot
provide roles or tenant membership. Provision one dedicated directory resolver
role with `USAGE` on the schema and `SELECT` only on `directory_subjects`,
`directory_sessions` and tenant-RLS-protected `audit_events`. The resolver
sets the resolved tenant scope before checking the latest signed-directory
audit marker and the digest of the complete current directory materialization.
Grant it `EXECUTE` on `directory_state_digest(text, text)`. The resolver
connection has no generic SQL endpoint and
is never shared with a request/user credential. Its lookup must be global
because tenant identity is not known until that lookup succeeds. Provision a
separate IAM sync writer with `SELECT, INSERT, UPDATE` on
`directory_subjects`, `SELECT, INSERT, DELETE` on `directory_sessions`,
`INSERT` on `directory_sync_events`, `SELECT, INSERT` on tenant-scoped `audit_events`,
`EXECUTE` on `directory_state_digest(text, text)`, and sequence usage. To invalidate active
plan authority in the same transaction, it also needs `SELECT, UPDATE` on
`plan_authority_state`, `SELECT` on `plan_approvals` and `operation_jobs`, and
`INSERT` on `plan_revocations`. Both roles must be NOSUPERUSER NOBYPASSRLS.
Do not grant directory table access to HTTP, worker, or ordinary authority
runtime roles. The IAM sync accepts only a full canonical JSON subject snapshot
with a detached signature from the configured Ed25519 public key. Generation
numbers advance monotonically, replacing all sessions and role grants; an IAM
change increments epochs for existing approvals/jobs of the changed subject.
Migration `0012` appends a `DIRECTORY_SYNC` audit marker for each existing
directory subject while directory writes are locked. New signed snapshots
append the marker in the same transaction as the grants, sessions and epoch
changes. The marker binds the latest signed digest and generation plus a
digest of the complete materialized row and session set, without copying
session identifiers or grants into audit details. A resolver rejects the
directory row if its latest audit marker differs, including after a selective
restore or edit of mutable directory state. Audit chain checkpointing
further detects a stale whole-database prefix. Deploy the migration and
corresponding resolver/writer together; checkpoint the new audit suffix
before releasing the site under its configured lag policy.
The backfilled marker does not establish that a pre-cutover materialized row
was genuinely sourced from IAM. The resolver accepts only a marker bearing
the provenance emitted by the post-cutover signature-verifying writer. For
each existing subject, the IAM connector must send a fresh, signed, full
subject snapshot with a generation higher than the stored one. Replaying an
identical old generation leaves the subject held. Keep authentication held for
unrefreshed subjects; checkpoint the resulting audit suffix before site
release. This cutover cannot be satisfied by a database edit or by marking
the 0012 backfill as trusted.
The signed `issuedAt` must also be later than the backfill marker's
`occurred_at`; signed snapshots generated before cutover are rejected even if
their generation is higher. IAM connector clocks must not issue future-dated
snapshots, and its timestamp has whole-second precision.

Migration 0010 records the namespace, first external start time, configured
history deadline, payload digest, and accepted run ID. The dispatcher commits
the immutable start attempt before calling Temporal. Set
`start_history_retention_seconds` to no more than the *guaranteed* namespace
retention, accounting for policy changes and outages. Unacknowledged attempts
past this window are held for independent workflow/native observation; never
reset the timer or retry by workflow ID after history may be gone. A returned
run ID is committed with the outbox acknowledgement and cannot be rewritten.
Migration `0011` offers `lock_job_scope(text, text, text)` to the read-only
workflow Activity role. Grant it `EXECUTE` on that function and `SELECT` on
`operation_jobs`; it does not need UPDATE permission to hold the job row stable
while checking current authority in its own transaction.

Migration `0013` registers environment enrollment under the verified tenant
and security-domain scope. Grant the API/runtime role `SELECT, INSERT` on
`environment_registrations`; the existing scoped audit INSERT records the
registration. Other roles do not need access to this table. Migration `0014`
adds `lock_native_worker_scope(text, text, text)` for a dedicated site worker
role. Grant that role `EXECUTE` on this helper and the existing job, authority
and worker lock helpers; grant `SELECT` only on `operation_jobs`,
`worker_grants`, `enterprise_records`, `audit_events`, `plan_approvals`, and
`native_containment_holds`. It must have no DML, DDL or table ownership.
Migration `0012` preserves all four worker certificate/revocation actions from
`0007` while adding `DIRECTORY_SYNC`; the isolated upgrade test seeds worker
audit history before applying `0012` onward. Migration `0015` reasserts this
same allowlist for draft preview databases that already applied the earlier
`0012` bytes. Since this branch is unreleased and migration checksums are
enforced, any disposable preview database with the old `0012` checksum must
be rebuilt from a fresh bootstrap before using this revision. Do not rewrite
its ledger or add a runtime compatibility path.

Before `0016`, the database administrator creates the restricted NOLOGIN
`hosting_site_worker_roles` group. A dedicated site login belongs only to
that group and is bound by the migration owner to one organization, tenant and
site in `site_worker_role_bindings`. Migration `0016` restricts its table reads
to live, admitted work for that binding; `0017` applies the same `session_user`
check inside the lock functions. The site login cannot make another tenant or
site visible by setting `app.*` or switching roles. The migration also binds
existing jobs to their admitted workload revision; an ambiguous old job stops
the upgrade for reviewed state conversion.
Migration `0018` excludes privileged administrative sessions that use `SET ROLE`
for isolated tests from the site-login classifier; it retains the binding for
real non-superuser site logins and the restrictive row policies.

Migration `0019` adds append-only discovery campaigns, generations, native
observations, and candidate absences under tenant RLS and an exact immutable
environment selector. Only comparable COMPLETE generations can propose an
absence. A candidate is not a tombstone, owner release, or execution grant.
Provision a separate `NOSUPERUSER NOBYPASSRLS` discovery ingestion LOGIN role
with `SELECT` on `environment_registrations`, `SELECT, INSERT` on the four
discovery tables, and `INSERT` on `audit_events`. Each campaign and published
generation adds an exact-digest event to the tenant audit chain in the same
transaction. Grant the API runtime `SELECT` on the discovery tables only.
Site worker logins receive no discovery table privilege. The ingest role needs
no UPDATE, DELETE, TRUNCATE, or other control-plane DML. The repository refuses
publication without a production verifier that independently checks signed
issuer authority, active collector enrollment, read-only native credentials,
and result provenance at each call. External signed audit checkpoints must
still be evaluated before site release after a database restore. A human
declaration or B10 mutation grant cannot establish any of those facts. The
isolated CI verifier is test-only.

The audit/history trigger forbids UPDATE and DELETE, and the restricted runtime
role cannot TRUNCATE or change the trigger. Migration `0008` chains every
tenant audit row in commit order with a sequence and content hash, including a
locked backfill of older rows; its stream head must be checked against the
independent signed checkpoints to detect a stale or truncated prefix. Database
administrators and backup operators still have privileged access. Independent
signed checkpoints and external evidence retention are delivered by B13. Back
up the entire database,
including `schema_migrations`, `enterprise_record_history`, `audit_events`,
and ownership lease epochs. A restored site remains observation-only until it
reconciles native ownership and stale epochs (B44).

Owner leases fence cooperative workers; they do not fence a guest, hypervisor,
storage writer, or external administrator. An expired lease remains held and
cannot be automatically reacquired. Recovery requires an independently reviewed
reconciliation operation in B11. A lease expiry alone cannot authorize another
production writer. The route must separately prove native exclusion.

## Application drafts and immutable history

Migration `0020` retains independently signed assessment inputs separately from
runtime-issued assertions. Migration `0021` adds `application_draft_revisions` for
unreviewed human proposals, with exact environment/generation/result foreign keys,
consecutive revisions, append-only history, tenant FORCE RLS and explicit site-worker
exclusion. Grant only the API runtime SELECT/INSERT on the new table plus its existing
discovery SELECT and audit INSERT/sequence privileges. The runtime must not have
UPDATE/DELETE/TRUNCATE, trigger ownership or a generic SQL endpoint. Discovery ingest
and site-worker roles need no proposal-writing privileges.

Apply 0021 through the existing checksum-bound runner. Its added uniqueness constraint
on discovery generations may lock/index existing data; plan the reviewed deployment
window accordingly. It performs no ownership or approval conversion. Original
inventory, drafts, audit checkpoints and migration history must survive restore
together; the disposable restore gate explicitly checks the new table. See
[the application-draft contract](../../../../docs/engineering/application-drafts.md)
for exact scope, retry, source-lock and operational limitations.
