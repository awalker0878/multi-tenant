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
HTTPS Vault Transit sign/verify API. The clients take separate short-lived
token providers, an explicit TLS trust context, and a bounded timeout. The
signer does not read the private key; the verifier has a trust map from stable key
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
Signed IAM directory changes also append a scoped `DIRECTORY_SYNC` marker in
the same transaction. The login resolver compares the live signed generation,
payload digest and complete materialized state digest with its latest audit
marker, so a selective directory rollback cannot restore an older session.
Checkpoint and restore the tenant audit
stream alongside directory state; session IDs and role grants are absent from
the audit marker.
Migration 0012 backfills a state marker for historical directory rows, but
that marker cannot authenticate users. The resolver requires provenance from
a newly verified, higher-generation signed full-subject IAM update before an
existing subject can log in after cutover. A replay of the same generation
does not promote the historical marker.

## Installed checkpoint runner and mutation hold

Install the `controlplane` extra and run `hosting-evidence` with a dedicated,
non-superuser PostgreSQL runtime role. It has four modes:

```sh
hosting-evidence inspect --organization-id org-a --tenant-id tenant-a
hosting-evidence enroll --organization-id org-a --tenant-id tenant-a \
  --expected-audit-sequence 0 --expected-audit-head <64-character-attested-head>
hosting-evidence verify --organization-id org-a --tenant-id tenant-a
hosting-evidence checkpoint --organization-id org-a --tenant-id tenant-a
hosting-evidence run --organization-id org-a --tenant-id tenant-a --interval-seconds 10
```

Before first enrollment, an operator independently compares
`inspect_baseline()` with an approved pre-enrollment export. An existing
tenant's sequence may be nonzero. The runner never silently enrolls a missing
checkpoint. Run one supervised `run` process per authorized tenant. Failure
exits nonzero so the supervisor alerts; a repaired service resumes by
checking the existing signed prefix. Keep the runner separate from the API
and rotate its scoped Vault/S3 credentials through protected agent files.

The installed `hosting-api` requires all settings below plus a protected JSON
scope inventory file, such as
`[{"organizationId":"org-a","tenantId":"tenant-a"}]`. It verifies every
listed scope at startup. Every authenticated tenant mutation also verifies
its own scope, including a newly enrolled tenant absent from the startup
inventory. The API refuses new workload drafts, approvals and job admission
with `EVIDENCE_HOLD` (503) when a signature, retained object, database chain or
configured lag cannot be proven. Approval revocation remains available to
remove authority during an incident. Installed Temporal dispatcher and
projector modes require the same gate and hold their job mutations; a claimed
outbox lease can expire and retry after repair without starting a workflow.

| Environment variable | Required value |
| --- | --- |
| `HOSTING_RUNTIME_DSN` | Product runtime PostgreSQL DSN with `sslmode=verify-full`; the workflow dispatcher/projector also sets identical `HOSTING_WORKFLOW_POSTGRES_DSN` |
| `HOSTING_EVIDENCE_S3_ENDPOINT`, `HOSTING_EVIDENCE_S3_REGION`, `HOSTING_EVIDENCE_S3_CA` | Approved HTTPS S3-compatible Object Lock endpoint, region and CA file |
| `HOSTING_EVIDENCE_S3_ACCESS_KEY_ID`, `HOSTING_EVIDENCE_S3_SECRET_FILE` | Scoped key ID and private 0600 secret file; no secret in a URL |
| `HOSTING_EVIDENCE_ARTIFACT_BUCKET`, `HOSTING_EVIDENCE_CHECKPOINT_BUCKET` | Separate retained artifact and independently administered checkpoint buckets |
| `HOSTING_EVIDENCE_RETENTION_DAYS`, `HOSTING_EVIDENCE_MAX_UNANCHORED_COUNT` | Site retention and maximum permitted unsigned suffix; zero requires checkpointing between audited writes |
| `HOSTING_EVIDENCE_VAULT_URL`, `HOSTING_EVIDENCE_VAULT_CA`, `HOSTING_EVIDENCE_VAULT_VERIFY_TOKEN_FILE` | HTTPS Transit endpoint, CA and private 0600 verification Agent token file |
| `HOSTING_EVIDENCE_VAULT_SIGN_TOKEN_FILE` | Runner only: separate private 0600 signing Agent token file; omit from API, dispatcher and projector |
| `HOSTING_EVIDENCE_VAULT_MOUNT`, `HOSTING_EVIDENCE_VAULT_KEY`, `HOSTING_EVIDENCE_VAULT_KEY_ID` | Exact Transit sign key and stable trust label |
| `HOSTING_EVIDENCE_VAULT_TRUST_JSON` | Explicit trust mapping, e.g. `{"evidence-2026":["transit","checkpoints"]}`; retain older labels until their checkpoint horizon or deliberately hold revoked streams |
| `HOSTING_EVIDENCE_SCOPES_FILE` | API startup inventory only; owner-protected JSON array of tenant scopes |
| `HOSTING_EVIDENCE_S3_PREFIX`, `HOSTING_EVIDENCE_S3_KMS_KEY_ID` | Optional namespace prefix and storage encryption key |

The product runtime role needs the existing evidence stream/entry grants and
`SELECT` on `audit_streams` and `audit_events`. The checkpoint process needs
the same evidence DML for first-use enrollment. The API and projector perform
full chain and retained artifact verification at each gated mutation. This is
deliberately conservative but can become expensive with large tenant audit
histories: benchmark it against the site portfolio and retain the hold if
verification exceeds its SLO. A future authenticated incremental index may
optimize reads only after preserving the independent full verification gate.

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
