# Signed assessment evidence ingestion

This internal workflow supplies installed product observations, directed route
claims and independently reviewed control findings. It does not run a migration,
approve execution, discover a platform, or establish native qualification by
itself. Reviewers sign only conclusions supported by independently collected
native evidence. A declared environment supplies a selector, never a conclusion.

## Runtime composition

Apply migration `0020_assessment_inputs.sql` using the migration role. Grant the
ordinary runtime role `SELECT` on `hosting_controlplane.assessment_inputs` only.
Configure all three assessment settings together:

| Setting | Required value |
| --- | --- |
| `HOSTING_ASSESSMENT_TRUST_PATH` | Protected local authority-signed policy file |
| `HOSTING_ASSESSMENT_AUTHORITY_PUBLIC_KEY` | Base64 raw 32-byte Ed25519 root public key |
| `HOSTING_ASSESSMENT_MINIMUM_REVISION` | Independently retained positive policy revision floor |

The composition classes are `SignedFileAssessmentTrustStore`,
`AssessmentInputRepository` and `DurableAssessmentInputs`. The HTTP handler
binds its already authenticated bearer credential with `inputs.bind(credential)`
for one call to `AssessmentService`. The bound provider re-authenticates through
the existing authority service and live role directory for every operation.
It requires `JOB_READER` or `EXECUTION_OPERATOR` on each exact native scope.
Credentials stay in request memory and are never persisted in evidence.

Missing installation proof refuses assessment. Missing route/control evidence
remains an explicit unknown. Invalid, expired, revoked or tampered retained
evidence refuses use; the reader never falls back to an older revision.

## Trust policy

The protected file contains `{"policy": {...}, "signature": "base64..."}`.
Sign the canonical ASCII JSON of `policy` using the separately controlled root
private key: sorted keys, compact separators, escaped non-ASCII, no nonfinite
numbers. Do not put root or reviewer private keys on the API host.

The policy has these exact fields:

```json
{
  "format": "hosting-assessment-trust-policy/1",
  "revision": 1,
  "issuedAt": "2026-09-28T15:00:00+00:00",
  "expiresAt": "2026-09-29T15:00:00+00:00",
  "enrollments": [],
  "revokedEvidenceIds": []
}
```

Every enrollment has `keyId`, `subjectId`, `role`, `publicKey`, `environments`,
`notBefore`, `expiresAt` and `revokedAt` (nullable). Each environment entry has
`environmentId` and the full seven-field `scope` (`organizationId`, `tenantId`,
`locationId`, `securityDomainId`, `endpointId`, `nativeScopeId`, `platformFamily`).
There are no wildcards. Enrollment roles are `INSTALLATION`, `SOURCE_EXIT`,
`TARGET_OPERATE`, `POLICY_TRANSLATION`, `SECURITY_EQUIVALENCE` and
`RECOVERY_READINESS`. Distinct roles require distinct subjects and public keys.
A control reviewer must be enrolled for both source and destination environments.

Policies live at most 24 hours. Replace the file atomically with a root-signed
higher revision; it must be a regular, owner-controlled file, neither group nor
world writable. Every use reloads it. Revoking/removing a key or adding an artifact
ID to `revokedEvidenceIds` blocks existing database evidence immediately on the
next verification. Preserve and advance the independently configured revision
floor across restart and restore; an in-process high-water mark alone cannot
detect a restored old policy after restart.

## Internal ingestion

Provision a dedicated `NOSUPERUSER NOBYPASSRLS` SQL login with no site-worker
membership. Grant `USAGE` on the schema; `SELECT, INSERT` on `assessment_inputs`;
`SELECT` on `environment_registrations`; and the existing constrained audit
insertion privileges needed by `audit_events`. Do not grant UPDATE, DELETE,
TRUNCATE, broad schema DML, directory writes, job authority or ownership access.
Never give this login to the API process. Construct a separate
`AssessmentInputRepository(connect, trust, ingest_role='hosting_assessment_ingest')`.

The `ingest(ctx, document, signatures)` method accepts independently signed
artifacts. `signatures` is a tuple of exact `{"keyId", "signature"}` records.
Each signature covers the complete canonical artifact, not only a digest or a
selector. The artifact fields are `format` (`hosting-assessment-evidence/1`),
`evidenceId`, `kind`, `revision`, `issuedAt`, `expiresAt`, and `payload`.
Validity must be positive and no longer than 30 days, contained in signer
enrollment validity. The database clock decides ingest freshness. Revisions must
increase for the exact binding, and evidence IDs are never reused.

| Kind | Exact payload fields | Required signatures |
| --- | --- | --- |
| INSTALLATION | `environmentId`, `installation`, `nativeEvidenceDigest` | INSTALLATION |
| ROUTE | `sourceEnvironmentId`, `destinationEnvironmentId`, `route`, `maturity`, `evidence` | SOURCE_EXIT and TARGET_OPERATE |
| CONTROL | `sourceEnvironmentId`, `destinationEnvironmentId`, `route`, `control`, `outcome`, `evidenceDigest`, `observedAt`, `sourceRawSnapshotDigest`, `destinationRawSnapshotDigest`, `sourceSnapshotDigest`, `destinationSnapshotDigest`, `normalizerVersion` | Role matching `control` |

`installation` contains `scope`, `productTupleId`, `productTupleDigest`; `route`
contains `source` and `destination` installations plus `method`, `guestProfile`,
`networkMode`, `dataMode`. Use `installation_document` and `route_document` to
produce these exact shapes. Each ROUTE `evidence` entry has `side`, `evidenceId`,
`evidenceDigest`, `observedAt`, `expiresAt`. These are source-exit and
target-operation campaign conclusions; the engine still checks independent,
current, exact tuple evidence before returning a candidate route.

CONTROL evidence binds both original and normalized generation digests with
`normalizerVersion` equal to `hosting-assessment-normalizer/2`. An original
discovery digest alone cannot approve transformed assessment facts. Every control
has its own reviewer and evidence digest. A replacement generation or tuple
requires new matching reviews.

Ingestion retains the canonical artifact, all signatures, original signed trust
policy, policy revision/digest, reviewer subjects and database verification time.
It appends an audit event in the same transaction. Readback verifies both original
custody proof and current authority policy. External signed audit checkpoints and
the deployment policy floor still govern whole-database restore or rollback;
database append-only rules alone cannot detect an administrator restoring history.
