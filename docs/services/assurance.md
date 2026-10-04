# Assurance service

Status: proposed service specification. Runtime: Laravel/PHP; destination: `services/assurance/`. Owner: quality/assurance with security, records and receiving operations owners.

## Purpose and responsibility boundary

Maintain protected, attributable evidence and decide which exact claims it supports. Publish qualification and operational acceptance with explicit conditions, limitations, expiry and retest triggers so the product never mistakes an implemented adapter for a supported service.

Assurance does not create native effects, approve execution, change plans or declare an entire vendor family supported. Evidence collection and independent acceptance are distinct roles. Successful upload is not qualification; qualification is not production change authorization.

## Owned aggregates and invariants

| Aggregate | Rule |
| --- | --- |
| EvidenceRecord | Tenant, campaign/job/operation/plan references, producer identity, artifact digest, capture time, custody and retention policy. |
| Upload / finalization | Bound permitted object location, size/type/expiry constraints, staged disposition and independently verified digest. |
| QualificationCampaign | Approved scope/method, tuple, required cases, observers, artifacts, limitations and candidate status. |
| QualificationDecision | Immutable reviewer decision on exact source/target/operation/method/guest/data/policy/topology/artifact tuple with validity/retest triggers. |
| Acceptance / support publication | Receiving-owner acceptance and versioned supported-capability view, derived from current applicable decisions. |
| Revocation / impact assessment | Attributable withdrawal or affected-scope decision preserving original evidence/history. |

E0–E4 retain the meanings in [requirements and qualification](../implementation/requirements-and-qualification.md). Neither a test result string nor an implementation completion flag advances evidence level. Changed artifacts/tuples require impact analysis and the required reruns; unchanged-scope reuse is an explicit decision.

## Proposed API surface

Routes use `/v1/tenants/{tenant_id}`. Shared platform qualification uses an expressly authorized publication scope; cross-tenant artifacts never become readable merely because support is published.

| Method and route | Contract |
| --- | --- |
| `POST /evidence-uploads` | Authorize staged upload, constrained location/content bounds and expiry; no reusable broad storage credential. |
| `POST /evidence-uploads/{id}/finalizations` | Independently verify artifact bytes/hash, provenance and referenced scope; commit immutable evidence or quarantine/reject. |
| `GET /evidence/{id}` | Authorized metadata and separately authorized short-lived artifact access where permitted. |
| `POST /qualification-campaigns` | Register explicit approved lab/test scope and required cases; campaign registration itself grants no execution authority. |
| `POST /qualification-decisions` | Independent reviewer records supported/limited/rejected result and exact evidence/tuple scope. |
| `POST /qualification-decisions/{id}/revocations` | Append withdrawal/retest trigger; maintain immutable history and notify consumers. |
| `GET /supported-capabilities` | Filter exact operation/tuple/artifact conditions; distinguish implemented, qualified and operationally accepted states. |

Lifecycle/worker evidence upload reports actual observations and attempt IDs. The caller cannot declare its own artifact independently observed merely by setting a JSON flag; observer identity and review rules are validated.

## Authorization and bootstrap

Governance grants distinct evidence-producer, evidence-reader, qualification-reviewer and operational-acceptance scopes. Validate actor/service identity and tenant/campaign/operation relationships. Approval of a job does not grant unrestricted access to guest data or evidence from another tenant.

P01 establishes protected storage/trust; P06.04 implements custody and decisions in simulation. Initial campaign definitions can exist without any qualification. Only an authorized isolated native campaign and independent review can create the first E3 claim; no bootstrap `supported=true` fixture enters operational admission.

## Consistency, retries and events

Use staged upload followed by idempotent finalization. Bind retries to the same object/digest/metadata and reject changed payloads. Finalization verifies stored bytes, then commits evidence metadata, receipt and outbox atomically. Storage and database do not share a transaction: reconcile orphan staged objects and failed finalizations without publishing unverified evidence.

Finalized artifact bytes cannot be silently replaced. Store corrected evidence as a new record linked to the original; retention/hold rules control deletion. Qualification decisions are append-only; current support view evaluates validity and revocation rather than overwriting historical review.

Publish `assurance.evidence.finalized`, `assurance.qualification.published`, `assurance.qualification.revoked` and `assurance.acceptance.recorded`. Consume job/operation references and artifact-change notifications for traceability/impact queues. Events do not replace immutable record validation or prove test success without underlying artifacts.

## Dependencies and failure behavior

Dependencies: governance, protected object storage/key custody, assurance database and authenticated producer/reference APIs. Missing bytes, digest mismatch, incomplete provenance or inaccessible verification inputs produce quarantine/hold. An object-store outage may permit bounded locally staged evidence only under an approved policy; qualification never proceeds without finalized required evidence.

Loss of mandatory evidence or assurance availability prevents new admission where current qualification cannot be established. Running jobs use the defined safe-point/evidence policy; do not fabricate success or immediately discard in-flight native observations. Retention policy and legal/records holds are resolved by accountable owners, not worker cleanup code.

## Deployment and operation

Separate API, verification workers and event publication under assurance ownership. Restrict evidence storage paths and keys by approved tenant/trust boundary; use immutable custody mechanisms selected in ADR-010. Download authorization is independent of knowledge of an object ID/URL.

Measure finalization backlog, digest/provenance failures, missing expected evidence, qualification expiry, revocation propagation and review age. Recover metadata, artifact versions, keys and custody rules together; verify referential consistency before republishing support. Test backup restore with real artifact verification rather than metadata counts alone.

## Verification and delivery

P06.04 custody/decisions; P07.06 first native dossier; P08/Q07 migration proof; P09 separate route expansion; P10/P11 operating acceptance. Requirements R04/R08/R13/R20/R24/R26/R29/R31/R35; Q01 and the relevant Q03–Q10 campaigns.

Test wrong tenant/campaign, forged observer, altered bytes, mismatched digest, repeated finalization, orphan upload, expired access URL, stale/revoked qualification, unsupported reverse route, changed adapter artifact and incomplete restore. Publishing a support row requires traceable evidence and reviewer decision, never only passing unit tests.
