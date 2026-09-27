# Evidence and audit checkpointing (B13)

This slice stores JSON receipts and manifests of at most 1 MiB by SHA-256
digest. PostgreSQL records tenant-scoped immutable evidence entries and a
per-tenant hash chain. A separate checkpoint store records a signed high-water
hash. Reads verify the signing identity, checkpoint scope, all chain links and
artifact bytes. A restored database older than its independent checkpoint is
held. The signing key never belongs in PostgreSQL or the artifact directory.

The caller obtains a trusted `TenantContext` from the authenticated server
principal and separately enforces operation and read policy. Do not expose
`initialize`, `append`, file paths or raw database connections to HTTP clients.
`initialize` is a one-time operator-controlled genesis action. If the external
checkpoint is later missing or invalid, reads and writes fail closed. A failed
checkpoint publish after a committed entry leaves an unanchored suffix; retry
the exact event key after restoring checkpoint service, or run the explicit
`checkpoint` operation under operator control. Never silently reset it.

`FileArtifactStore` and `FileCheckpointStore` remain single-host test adapters.
`S3ObjectLockArtifactStore` and `S3ObjectLockCheckpointStore` accept an SDK
client for a separately administered S3-compatible endpoint. They require
enabled bucket versioning and Object Lock, request per-object `COMPLIANCE`
retention, and read each version with its exact version ID. A missing, expired
or weaker retention setting, conflicting version, or delete marker fails
closed. Give audit checkpoints their own `stream='audit_events'` namespace;
evidence entries use `stream='evidence_entries'`. Prefer separate service
identities and buckets across both checkpoint streams and the artifact bytes.
The endpoint must implement real Object Lock semantics, not merely accept the
API parameters. Validate retention and restore behavior with the chosen
on-prem endpoint and a separate custodian before enabling a site.

`VaultTransitSigner` and `VaultTransitVerifier` use a separately administered
HTTPS Vault Transit sign/verify API. The client takes a short-lived token
provider, an explicit TLS trust context, and a bounded timeout. The signer
does not read the private key; the verifier has a trust map from stable key
labels to Transit mount/key names and rejects removed labels. Give signing
and verification separate Vault policies and tokens. Vault key rotation
preserves old signature versions only while policy permits verification;
retain old trusted labels through the evidence retention horizon unless a
revocation incident requires holding the stream. No Vault token belongs in
PostgreSQL, workflow history, an evidence object, or a URL. This adapter
depends only on Python's standard HTTPS client; the S3 adapter accepts a
provider SDK client (for example an approved boto3 client configured to the
sovereign endpoint). No external service credentials are included in tests.

Migration `0008_audit_chain.sql` adds a commit-order-safe sequence/hash to
every `audit_events` row. It takes an exclusive table lock and backfills
legacy rows by tenant and `event_id`, then restores append-only protection and
FORCE RLS in the same migration transaction. Plan a maintenance window for a
large audit table. Future audit inserts lock their tenant stream row in the
transaction, so a later sequence cannot commit before its predecessor. The
trigger runs under the non-superuser migration owner and does not grant an
application role UPDATE on audit rows or stream state. The runtime role only
needs SELECT on `audit_streams` to verify.

`AuditCheckpointRepository.inspect_baseline` returns the checked database
sequence and hash. A separately authorized operator must compare this with
the approved pre-enrollment export and pass both into `initialize`; a missing
external checkpoint after enrollment is an incident. `checkpoint` verifies
the entire chain before publishing a signed audit high-water mark. Run this
after durable audit commits and on a bounded schedule, alerting on
`unanchored_count`, failed signatures, missing objects, missing retention, and
checkpoint outages. During the unanchored window a privileged database
operator can alter the suffix; set the maximum acceptable lag in site policy
and hold mutation on a missed threshold. On database restore, keep the site
observation-only until both audit and evidence streams verify against their
independent checkpoint stores; a stale prefix cannot be accepted.

The JSON input guard refuses credential-shaped field names, URLs, long text,
and common secret-like values. It cannot prove arbitrary free text is
secret-free; producer-specific allowlisted receipt schemas and log/history
redaction remain needed for the B13 secret-leakage gate. Workload disk bytes and
large exports belong to scoped data movers, not this 1 MiB receipt store.

Runtime SQL grants: `SELECT, INSERT, UPDATE` on `evidence_streams`; `SELECT,
INSERT` on `evidence_entries`; `SELECT` on `audit_streams`; schema `USAGE`.
The migration role owns DDL,
the runtime role is `NOSUPERUSER NOBYPASSRLS`, and the signer/checkpoint
custodian must have a separate identity. Do not grant UPDATE or DELETE on
`evidence_entries`. The append-only trigger also prevents accidental mutation.
The S3/Vault adapters have fault-injection tests, but no deployed independent
retention/KMS service is available in this repository's CI; production
qualification and site policy remain deployment gates.
