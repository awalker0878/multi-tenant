# P03 Catalogue implementation and qualification

P03 engineering is delivered at source **1c51f56a928291870e5125508aeb04935583fd56**.
The [qualification index](../../verification/p03/final/qualification-index.json)
retains passing PostgreSQL and three-engine live campaigns with exact source/log
bindings. Evidence is committed at **187ead3a02521cc3d6be063c6f449f0e3b79113a**.
The [completion review](p03-completion-review.md) supplies the remaining operator
and independent-review tasks. P03 remains IN_PROGRESS and G03 NOT_REVIEWED until
those acceptance obligations are satisfied; automated passes do not supply the
missing human observations.

The user authorized P03 development on 2026-10-05 and continued it on 2026-10-06.
The accepted G00/DC03 baseline supplies initial logical cardinalities; ADR-013 now
records that existing scoped acceptance. P01/P02 receiving obligations remain open.

## Delivered behavior

Catalogue owns PostgreSQL application, workload, deployment and versioned reference
identities. Each immutable intent is a complete deployment/environment snapshot.
One application owns a workload identity; one deployment identity exists per
application/environment. WSD/domain sharing is explicit and same-tenant. New
publication requires current, non-retired reference versions; historical versions
remain readable. Reference names/zones cannot be reassigned and in-use current
references cannot retire.

Intent includes compute, guest, ordered disks/NICs, typed requirement strength,
failure-domain grouping, datasets, consistency/recovery objectives, dependencies,
services and acceptance criteria. Validation rejects invalid associations, ordinary
cross-domain NICs, dangling references and separate startup/shutdown cycles.
Communication may be bidirectional; controlled inter-domain communication is explicit.
ZIP is not a placement zone. Unsupported required controls survive for later planning.
Accepted integers remain within ±9,007,199,254,740,991, including values that overflow
PHP's native integer parser.

Strong application ETags serialize all deployment streams. Tenant/actor command
receipts bind the action, canonical command and expected revision. Matching retries
return the original result even after later edits; changed payload reuse conflicts.
Revision, current pointer, workload/reference associations, audit, receipt and outbox
commit atomically. Controlled SQL migrations are replayable; runtime roles cannot
mutate historical revisions, receipts, audit or reference versions.

Governance supplies current delegated authority and active owner membership in the
admitted scope through a strict owner-check contract. Reference administration is
separate from application authoring. Catalogue accepts no submitted actor authority,
reads no other service's database and treats no event as a new grant.

The Console uses generated contract clients and validates actual responses. It
delivers create/edit/full JSON import, structured intent, dependency/data views,
history and comparison. Invalid and stale submissions retain drafts. Structured
edits and imported drafts compare against the explicitly refreshed current revision.
An uncertain result locks the command for unchanged retry. Revocation and foreign
tenant denial redirect safely; encrypted history invalidation prevents Back from
restoring protected editor fields.

The bounded outbox command uses verified TLS and mandatory confirmed publication.
It retains event IDs across uncertainty and prevents pending facts overtaking an
older fact for the same aggregate. Committed facts can be delivered after the actor
is revoked. Planning's actual consumer remains P05 work.

## Measured qualification

GitHub Actions run **37405120516** passes all four P03 jobs at the stated source.
The [coverage matrix](../../verification/p03/check-matrix.md) maps checks to Q01/G03;
[corrections](../../verification/p03/corrections.md) preserve original failures.

| Campaign | Retained result |
| --- | --- |
| PostgreSQL/TLS core | 89 tests, 335 assertions, no skips/failures; migration replay, immutable-role denials, rollback and retry. Catalogue/Governance format, types and architecture gates pass. |
| Chromium live | 38 checks and one complete compiled journey; zero browser failures/skips/retries. |
| Firefox live | The same 38 checks and journey pass; zero browser failures/skips/retries. |
| WebKit live | The same 38 checks and journey pass; zero browser failures/skips/retries. |
| Local Console | 147 passed / 674 assertions; seven explicitly PostgreSQL-gated skips. Format, types, architecture, Vue typecheck, production build and ten frontend boundary controls pass. Hosted P02 identity separately passes on final source. |
| Local intent/generation | 24 domain cases / 40 assertions; generated PHP/Python/TypeScript clients match the versioned source. |

Every live run exercises real current authority, concurrent HTTP requests, process
restart and broker faults. The observer sees 11 deliveries for 10 distinct event IDs
after actual publication followed by an injected pre-commit exception. Replay
preserves identity and ordering. The browser's lost accepted response produces
exactly four revisions; independent PostgreSQL counts pair audit and outbox.
All four corresponding facts are then observed after membership revocation.

The large tenant has 10,001 applications and a separate tenant has 1,001. Pages
contain 50 entries and 6,812–6,817 bytes. Captured index scans read 51 rows with
observed execution times 0.081–0.188 ms. A separate 501-row core case asserts one
local SQL list query. These are metadata-skew measurements, not production capacity
or maximum-document population claims. Bounds are 256 KiB intent, 100 workloads,
200 datasets, 500 dependency edges, 100 services, 100 deployment streams per
application and 50 entries per page. Database statement/lock/idle-transaction
defaults are 5/3/15 seconds.

The five reports bind 475 unique source files. Archive digests, command-log hashes,
source bytes, JUnit cases, browser results and query-plan artifacts match the exact
Git source. Live services use distinct owned PostgreSQL databases and runtime roles.
PostgreSQL and RabbitMQ use verified TLS; application peers use private loopback
TLS proxies and the browser uses HTTP loopback. Synthetic OIDC transport exists
only in the separate principal bootstrap; live requests consult real Governance.

## Compatibility, operations and limits

Use [Catalogue 1.0.1](../../contracts/openapi/catalogue-v1.0.1.json), the strict
[intent schema](../../contracts/schemas/catalogue/intent-v1.json),
[owner-check API](../../contracts/openapi/governance-catalogue-owners-v1.json) and
[event schema](../../contracts/schemas/events/catalogue-intent-v1.json).
The original 1.0.0 document remains byte-for-byte history; its missing tenant
declarations are corrected by a new artifact without changing routes. No freeze
rule or required check was weakened.

The [runbook](../operations/runbooks/catalogue.md) defines migration, current trust,
retry and outbox recovery. The foundation readiness route still returns 503; no
operated readiness is claimed. Queue provisioning is delivered for the future
Planning consumer, with a separate observer in qualification. Native placement,
discovery and effects remain later phases.

The [regression receipt](../../verification/p03/final/regression-status.json)
records current-source package, image, contract, policy, Compose and P02 identity
passes. Unchanged messaging and Governance-event sources retain their separately
identified passes. Final-source Kubernetes run **37405120379** remains queued
behind earlier branch campaigns. The historical P01 Kubernetes pass is retained
as historical evidence, not transferred to the new source.

G03.04 requires representative operator and selected managed-browser/assistive
observations (BL-P03-001). G03.01–04 require accountable reviewers and independent
quality assessment (BL-P03-002). No native support, operating acceptance, human
accessibility review or G03 receiving decision is inferred.
