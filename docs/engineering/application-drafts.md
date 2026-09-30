# Revisioned application drafts over observed inventory

Reviewed 29 September 2026. This is the B17/B20 persistence and API increment in
[the existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
It records proposed application membership and dependency assertions. It does not
accept ownership, independently authenticate an asserted application owner, create
a migration plan, publish native inventory or authorize execution.

## Owners and separation of evidence

`provisioner/controlplane/discovery/grouping.py` owns proposal shape and validation.
Its `validate_draft` accepts distinct members actually present in a fresh stored
source, including partial inventory. The existing `reviewed_candidate` path still
requires complete observations and an exact independently verified owner review.
The valid candidate format/digest and its stricter review boundary are unchanged.

`discovery/application_drafts.py` owns canonical decoding, immutable draft revisions
and PostgreSQL transactions. `api/application_drafts.py` installs routes in the
existing authenticated control API; `api/server.py` composes the actual repository
with its established runtime connection. No alternate submitter, native credential,
CLI wrapper or platform-specific compatibility path is introduced.

The authenticated `recordedBy` subject and database `recordedAt` are not supplied
by the request. The proposed `ownerId`, dependency source and source reference are
assertions by that author, not proof that the named owner, CMDB, guest or monitoring
system approved the content. Signed original inventory remains in the discovery
store and is never overwritten with human assertions. Every saved/read draft has
`status: UNREVIEWED`, `ownershipAccepted: false`, `executionAuthorized: false`.

## Authenticated API

| Operation | Contract |
|---|---|
| `PUT /v1/environments/{environmentId}/application-drafts/{applicationGroupId}` | Append a revision. Requires exact native-scope `EXECUTION_OPERATOR`, live session and available evidence gate. The path and body application IDs must agree. |
| `GET /v1/environments/{environmentId}/application-drafts/{applicationGroupId}` | Read the latest draft revision; `?revision=N` selects exact history. Requires exact native-scope `JOB_READER` or `EXECUTION_OPERATOR`. |

The existing PUT/GET and new listing route use the same bearer/SSO authentication
and environment selector.
Unauthorized and absent resources return 404; missing authentication returns 401.
An inconsistent request returns 422, a changed revision/source returns 409, and an
unavailable store or evidence gate holds the operation. Responses are not cacheable.
The [operator continuation](application-draft-operator.md) now supplies bounded
listing and CLI save/load; the [browser workspace](application-draft-browser.md)
edits existing metadata and startup order. Delete and native ownership-acceptance
remain unimplemented. Draft-write endpoints cannot accept caller-supplied review records,
actor identities, native credentials or execution/ownership success flags.

The PUT body contains exactly `generation`, `resultDigest`, `expectedRevision`,
`draft` and `dependencies`, with JSON content type. Duplicate fields and an aggregate
over 128 KiB are rejected. `generation` is a positive signed-64-bit integer;
`expectedRevision` is an integer from zero through 2^63−2; booleans, floats and
numeric strings are not coerced. `resultDigest` is an exact lowercase SHA-256.

| Proposal field | Exact shape and limit |
|---|---|
| `draft` | Exactly `applicationGroupId`, `name`, `ownerId`, `members`, `datasetIds`, `consistencyGroups`, `startupOrder`. The name is bounded to 256 characters with no controls. |
| `members` | 2–100 objects containing `workloadId` and `nativeVm`. `nativeVm` is `[endpointId, nativeScopeId, platformFamily, "vm", nativeId]`. Both logical IDs and native identities must be distinct. |
| `datasetIds` | 1–1,000 distinct proposed dataset IDs; these are not observed storage attachments. |
| `consistencyGroups` | 1–100 objects containing `groupId` and `datasetIds`. Every proposed dataset occurs exactly once across the groups. This is asserted grouping, not verified write consistency. |
| `startupOrder` | Every selected logical member exactly once, consistent with all known `STARTS_AFTER` edges. |
| `dependencies` | Up to 500 objects containing exactly `assertionId`, `sourceWorkloadId`, `targetWorkloadId`, `relation`, `state`, `source`, `sourceReference`, `observedAt`, `unknownReason`. |

Identifiers use the existing bounded record-ID vocabulary. Relations are
`STARTS_AFTER` or `SERVICE_CALL`; sources are `CMDB`, `GUEST`, `MONITORING` or
`APPLICATION_OWNER`. A known target must name a different selected member. Unknown
edges have a null target and one of `UNRESOLVED_TARGET`, `NOT_OBSERVED`,
`CONFLICTING_SOURCES`, `EXTERNAL_DEPENDENCY`. Unknown dependencies are retained,
not dropped or silently converted into external members. Assertion times must be
UTC and lie between one hour before source capture and the current database time.
Equivalent UTC timestamp spellings are canonicalized before retry comparison.

## Snapshot binding, revisions and retries

A new revision requires the latest exact-scope discovery generation, its matching
result digest, and capture age no greater than one hour. The repository rebuilds
that generation from stored observations and verifies each object and the full
source digest. Every selected VM must exist in that source. A partial generation
is usable to draft known membership, not to prove complete coverage or absence.

Saving takes the same cooperative transaction advisory lock as source-generation
publication before checking currency. It rechecks live session/scope/evidence after
waiting, obtains fresh database time after hydration, writes the revision and audit
event in one transaction, and rechecks authorization before commit. Lock waits are
bounded to five seconds and SQL statements to ten seconds. These are database
operation bounds, not an estate-scale response-time guarantee.

The first append supplies `expectedRevision: 0`; subsequent edits supply the
currently read revision. Concurrent competing edits cannot both append at the same
expected revision. An exact retry by the same authenticated actor, with the same
source and canonical proposal at the immediately following revision, returns the
original record without a second audit event or changed timestamp. A different actor
or body conflicts. The service does not automatically rebase edits or recover a lost
response by silently choosing newer inventory.

Read/retry responses retain the original source pin and report `latestGeneration`
and `sourceSuperseded`. Historical reads remain available after newer inventory.
An identical retry can return an old source as superseded; it is not a new assessment.
`sourceSuperseded: false` only means that no later generation was seen by that read;
it does not attest freshness, completeness, current grants or native qualification.
A subsequent concurrent publication can still make a read response historical.

`hosting-application-draft-revision/1` binds environment, full scope, application ID,
revision, generation/result digest, proposal digest, authenticated author and database
time through `recordDigest`. The proposal retains the existing
`hosting-application-group-candidate/1` representation and digest. Readback verifies
canonical content and both checksums. Checksums detect inconsistent stored content;
they are not independent signatures or administrator-resistant custody. The existing
tenant audit chain and external evidence checkpoints remain required for restore.

## PostgreSQL and upgrade obligations

Packaged migration `0021_application_drafts.sql` adds an append-only revision table,
exact-scope environment and generation/result foreign keys, consecutive-revision
validation, tenant FORCE RLS and a restrictive site-worker exclusion policy. SQL
status cannot become APPROVED. Historical UPDATE/DELETE are prohibited. No role is
created by this migration. Grant the trusted API runtime only SELECT/INSERT on the
new table and retain its existing scoped discovery-read/audit permissions; do not
grant the collector, ingest or site worker proposal-writing privileges.

The migration adds a source-generation uniqueness constraint for the exact result
foreign key. Plan for its database locking/index cost in the reviewed deployment
window. Apply through the existing checksum-bound migration runner, not by editing
old migration files. No previous candidate is imported as an accepted application.
A restore must retain revisions, original generations, audit chain and migration
ledger together. The disposable restore gate now explicitly requires this table.

PostgreSQL [row security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)
and [advisory locking](https://www.postgresql.org/docs/17/explicit-locking.html),
consulted 29 September 2026, explain the underlying mechanisms. Custom tenant
settings are not authentication; privileged administrators and BYPASSRLS roles
remain outside those protections. Source locks coordinate these application owners,
not arbitrary SQL clients or native writers. Independent recovery evidence and
reviewed database grants are still deployment obligations.

## Tests and remaining B17 work

Contract tests cover canonical proposals, bounds, actual member selection, partial
versus reviewed inventory, startup conflicts and explicit unknowns. API tests cover
SSO scope, authenticated attribution, schema rejection, live revocation, evidence
holds and foreign/approval response rejection. Disposable PostgreSQL tests cover
append/history, canonical retries, competing editors, source changes, lock-wait
revocation, atomic audit rollback, SQL guards, tenant/worker isolation and actual
HTTP-to-database composition. The existing restore and installed-package gates
cover the new records and actual package owners. Report final-revision CI separately
from local runs; these are not native platform qualification campaigns.

The separate signed owner-review path below now persists and evaluates exact-draft
assessment decisions. B17 remains partial: independently verified external source
enrichments, owner enrollment/signing integration and application-wide destination
assessment remain open. Scoped listing, CLI save/load and bounded existing-draft
browser editing are implemented; full browser creation/member/evidence editing is
still B20 work. No proposal bypasses later native provisioning, conversion,
fencing, transfer, cutover or recovery gates.


## Signed owner-review continuation

The [owner-review evidence contract](application-owner-review.md) now provides
independent exact-draft acceptance/revocation and GET-only candidate evaluation.
This is separate from draft saves, listing and editing; drafts remain UNREVIEWED.
The CLI/browser in this document do not issue signatures or show a native approval.
Owner-facing review integration, verified external dependencies and application-wide
migration planning remain open. The separate review does not change draft status,
create a native owner or authorize a migration.
