# Signed application-owner decisions for assessment

Reviewed 30 September 2026. This B17/B20 increment follows the
[existing wave plan](../product/enterprise-workload-mobility-execution-plan.md).
It connects independently signed owner decisions to retained application drafts
and a scoped read endpoint. It does not transfer native ownership, authorize
migration, verify third-party dependency evidence or change the draft's status.

## One evidence authority, not a browser approval flag

The existing `AssessmentInputRepository` and `SignedFileAssessmentTrustStore`
now recognize `APPLICATION_REVIEW` evidence and the `APPLICATION_OWNER` enrollment
role. No separate approval store, compatibility representation or issuer exists.
The deployment's independent root enrolls the owner's signing public key for the
exact environment and seven-field native scope. Its `subjectId` must match the
proposal's `ownerId`, and that subject must differ from the recorded draft editor.
Typing an owner ID does not create this enrollment. A source-exit, installation,
security or operator identity does not substitute for an application owner.
Owner enrollment cannot reuse the trust root key or another review role's
subject/key. Private signing keys remain outside the API and operator clients.

The owner signs the complete canonical `hosting-assessment-evidence/1` envelope,
using the existing signing/custody protocol. Its new payload contains exactly:

| Field | Binding |
|---|---|
| `environmentId`, `scope`, `applicationGroupId` | Exact retained environment, native scope and application proposal. |
| `draftRevision`, `draftRecordDigest` | Immutable saved revision and digest including its editor and timestamp. |
| `generation`, `resultDigest`, `proposalDigest` | Original inventory generation and exact complete proposed membership, data, startup and dependencies. |
| `ownerId`, `reviewReference` | Independently enrolled owner subject and owner-signed review reference. A reference is not independently verified ticket content. |
| `decision` | Only `ACCEPT_FOR_ASSESSMENT` or `REVOKE`; never an execution approval. |
| `reviewedAt` | UTC time no earlier than the persisted draft and no later than envelope issuance. |

The outer envelope retains `evidenceId`, `revision`, `issuedAt` and `expiresAt`.
A decision's complete validity is at most one hour from `reviewedAt`, contained
in enrollment validity. Each immutable draft has its own evidence revision stream;
acceptance and revocation share that stream. New drafts require new signatures,
not relabelled acceptance. Review evidence IDs cannot be reused. Exact current
retries retain their original artifact and audit identity; expired, revoked or
superseded acceptance cannot be reingested as a fresh decision.

## Ingest and concurrency

Only the existing separate assessment-ingest SQL role may append signed evidence.
For this kind, ingestion verifies the original saved draft's content/digests,
owner/editor distinction and observation binding. Acceptance requires the current
draft and inventory generation and a fresh, valid proposal. Partial observations
can support an owner decision about a draft; they still cannot produce a reviewed
assessment candidate. Revocation may target a retained historical/stale draft.

Ingest acquires the existing source-publication lock before the evidence-stream
lock. Draft edits and new inventory therefore cannot pass a currency check and
change before this decision is committed. Signatures and live trust are rechecked
after lock waits, including exact retries, and again after the audit append. This
post-wait/pre-commit correction applies to all assessment evidence kinds. Revoked
or expired authority rolls back the evidence and audit transaction together.

The read service takes the shared form of the same source transaction lock.
It verifies the retained original policy/signatures, reloads current owner
allocation/revocation, reconstructs the selected observation, and rechecks evidence
and reader authority before returning. Transaction locks protect cooperating
writers, not an administrator rewriting history or a restored database. Preserve
independent signed audit custody and policy revision floors across restart/DR.
PostgreSQL's [advisory-lock reference](https://www.postgresql.org/docs/17/explicit-locking.html#ADVISORY-LOCKS)
documents the transaction/shared lock semantics used here; bounded lock and statement
timeouts prevent indefinite waits. This is not an estate-performance qualification.

## Read-only API and candidate evaluation

With the existing assessment trust settings configured, `hosting-api` composes
`ApplicationReviewService` using the same draft and signed-input repositories.
No new secret, HTTP write endpoint or runtime database write permission is added.
The existing scoped `JOB_READER` or `EXECUTION_OPERATOR` can request:

```text
GET /v1/environments/{environmentId}/application-drafts/{applicationGroupId}/review?revision=N
```

An exact positive draft revision is required. This endpoint is read-only: POST,
PUT and DELETE do not issue decisions. Missing trust configuration returns 503;
an unknown/inaccessible draft is 404. Invalid, expired, revoked-key or tampered
signed evidence holds the read without falling back to earlier evidence. Native
scope and the same authenticated human subject are rechecked after database work.

The response is `hosting-application-review-status/1`. It retains the draft and
inventory references, current source/revision metadata, owner decision, evidence
ID/revision/digest, review validity and evaluation time. Its statuses are:

| Status | Interpretation |
|---|---|
| `UNREVIEWED` | No signed decision for this exact immutable draft. |
| `REVOKED` | The latest valid signed decision explicitly revokes this draft's review. |
| `HELD_SUPERSEDED_DRAFT`, `HELD_SUPERSEDED_INVENTORY` | Historical pins are not current assessment inputs. |
| `HELD_INCOMPLETE_INVENTORY`, `HELD_STALE_INVENTORY` | Owner acceptance cannot establish native visibility or refresh observations. |
| `REVIEWED_ASSESSMENT_ONLY` | Existing `reviewed_candidate` validation passed on complete, current observations. |
| `REVIEWED_WITH_UNKNOWNS` | The same validation retained unresolved dependency assertions explicitly. |

Only the last two states contain a `candidateDigest`; unknown dependencies remain
counted. Every state returns `ownershipAccepted: false`, `executionAuthorized: false`
and `dependencyEvidenceVerified: false`. Owner acceptance of proposed application
content is not native ownership acceptance, independently verified CMDB/guest/
monitoring evidence, or a migration approval. Stored drafts stay `UNREVIEWED`;
review validity is separately evaluated, never copied into immutable drafts.

This increment consumes owner decisions through the existing application-candidate
validator. It does not yet extend the per-VM destination comparison endpoint into
an application-wide migration planner. Browser/CLI owner-review presentation and
an enterprise signing/approval experience remain future integrations.

## Deployment and verification

Apply immutable migration `0022_application_review_evidence.sql` through the
existing checksum-verified migration process. It extends the assessment kind
constraint; no earlier migration, table ownership, RLS or immutable trigger is
rewritten. Deploy updated readers before publishing a policy containing the new
role: older readers reject unknown roles/kinds rather than silently accepting them.

The assessment-ingest role additionally needs SELECT on
`application_draft_revisions`, `discovery_generations` and `discovery_observations`
to validate the retained references. Do not grant modification rights on those
tables, extra runtime DML, site-worker access or signing-key custody. Runtime
SELECT on signed evidence remains sufficient for review reads. Constraint changes
can require an exclusive lock and table scan; schedule the migration accordingly.
See the [PostgreSQL ALTER TABLE reference](https://www.postgresql.org/docs/17/sql-altertable.html)
for that deployment consideration. Both primary references were consulted on
30 September 2026; neither is evidence of installed platform qualification.

Tests use real ephemeral Ed25519 signatures and synthetic inventory. They cover
owner/scope/draft binding, independent roles, validity, revocation, partial/unknown
facts and candidate-only outputs. Separate PostgreSQL tests exercise isolated
writer/RLS rights, exact retry, new draft/inventory holds, post-lock and pre-commit
revocation, atomic evidence/audit rollback and authenticated API consumption.
Installed distributions include the actual owners and migration. Local database
skips and final-revision CI results must be reported separately.

B17/B20 remain partial: verified external dependency evidence, actual owner/key
onboarding, application-wide comparison/planning and guided browser/CLI owner
review remain open. The existing B22 scheduling, visibility reconciliation, native
fact, provisioning, transfer, fencing, cutover, recovery and qualification work
is unchanged. No native environment, workload or production dataset was contacted.
