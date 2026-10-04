# Recover persistent dependencies

Procedure ID: OPS-DEPENDENCY-RECOVERY. Owners: SRE and the affected persistence/identity owner; lifecycle coordinates consistency. Scope: R02/R15/R16/R29–R32/R35; P01.05/P01.06, P10.02; Q09. Use for database, workflow, broker, object-store, state or trust failure where restart/failover/restore can alter durable observations.

## Determine the recovery class

Distinguish a process restart with intact durable state, a supported failover with a known replication point, and restoration from older or partial state. Use dependency-native health and recovery metadata to determine the class; a responsive endpoint does not prove that the latest writes survived.

If any acknowledged data may be lost or diverged, invoke [restore control plane](restore-control-plane.md) and the common [recovery reconciliation](recovery.md). A single repaired dependency must not reopen mutation while its related stores remain inconsistent.

## Inputs and preconditions

Record affected component/environment/release, incident ID, failure time, current leader/replica/storage state, last trusted checkpoint, retention/replay horizon, encryption/key versions, supported recovery procedure/bindings, operation scope and dependency owner. Confirm isolated recovery capacity and protected backup access.

Inventory dependent services and active jobs, then hold unsafe new admission/dispatch. Fence old native workers if restored authority or journal data could overlap their still-valid execution. Preserve read-only observation and original failed storage/backups. Do not initialize an empty database, broker namespace or object store under an existing production identity to make health probes green.

## Recovery sequence and checks

| Dependency | Owner action | Expected observation / escalation |
| --- | --- | --- |
| Identity/PKI/key custody | Establish independently authenticated recovery access; recover required trust/key versions; validate signatures/decryption and reconcile revocation state | Required data decrypts and callers validate within scope; unavailable key or uncertain current authority holds dependent service |
| Context PostgreSQL | Use recorded supported failover/restore method; recover selected point; validate schema, tenant/resource identities, idempotency, operation and outbox/inbox records | Counts/digests and recovery watermark match selected evidence; detect later/missing transactions; no cross-context runtime access |
| Temporal persistence/server | Restore compatible persistence/configuration using supported owner procedure; keep dispatch isolated; compare workflow IDs/history with lifecycle jobs | Histories readable by selected versions; each history maps to intended job; unmatched/later history held |
| Event broker | Recover permitted retained messages/offsets and topology/ACLs; compare producer outbox and consumer inbox watermarks | Lost/duplicate/gap scope explicit; controlled replay only after owner records reconciled |
| Evidence objects/metadata | Restore required bytes and keys without overwriting retained immutable objects; compare assurance references and digests | Every required evidence object validates or is quarantined/missing; absent artifact never becomes a valid claim |
| IaC/state backend | Restore protected state and lock metadata in isolation; independently inspect actual native resources and field owners | State/native binding agrees or remains held; stale lock removal requires proven writer exclusion |
| Cache/projections | Rebuild only from reconciled authoritative records with appropriate tenant permissions | Derived views match source revision/freshness; cache content cannot restore current authority |

These are logical dependencies, not a universal product command sequence. Follow the selected versions' exercised bindings and recover dependencies in an order that provides required trust, durable state and connectivity. Keep incompatible partial restores isolated.

## Controlled replay and reconciliation

1. Compare the last durable producer transaction, outbox dispatch, broker retention and consumer receipt for each affected channel. Identify recoverable duplication separately from missing facts.
2. Reconstruct only facts justified by authoritative retained records. A missing outbox record cannot be invented from a guessed user intent; record the gap and owner resolution.
3. Replay through reviewed consumer contracts under bounded rate with existing deduplication identity. Observe tenant isolation, backlog and errors.
4. Prevent replay from issuing native effects, approvals or current grants. Lifecycle reconciles its operation journal and actual native outcomes before dispatch resumes.
5. Preserve evidence of original gaps, replay boundaries and resulting projections. Do not delete retained messages or consumer receipts to force a clean run.

For point-in-time recovery, list effects accepted externally after the selected recovery point. Reconcile authoritative request IDs/resources and reservations. Restore cannot erase their real existence or justify repeating them.

## Stop conditions

Stop on unknown recovery point, failed integrity, unavailable key, incompatible schema/history, unresolved split brain, inaccessible native readback, unknown live writer, insufficient retention to reconstruct required facts or overbroad recovered credentials. Preserve the affected hold and escalate to the owner; a fresh empty service or a global lock reset is not a valid repair.

If the attempted restore fails, retain original backup and current recovered state for diagnosis. Select another known recovery point only with explicit impact analysis on data loss, external effects and accepted objectives. Keep each attempt attributable.

## Verification and handover

Check durable identities/counts/digests, schema/API compatibility, private-store access denial, decryption, backup health, workflow readability, controlled replay and evidence references. Restart once within the exercised scope to establish restored persistence survives normal service recovery; avoid broadening tests without a remaining risk.

Return a dependency recovery report with exact recovered point/watermarks, actual data gap, incompatible/held records, commands/bindings and outputs, measured time and operator/reviewer references. Lifecycle uses it in [recovery](recovery.md) to reconcile authority/native state. Healthy dependencies alone do not reopen admission or declare application recovery.
