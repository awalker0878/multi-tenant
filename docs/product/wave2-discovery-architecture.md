# Wave 2 read-only discovery and comparison

Status: implementation design for B14–B22. No native route is qualified by
this document or by a fixture-backed test.

## Authority and state boundaries

An `EnvironmentRegistration` is a human selector in `DECLARED_UNVERIFIED`
state. It is not an observed environment, endpoint enrollment, ownership claim
or permission to contact a platform. The B10 `DISCOVER_READ` grant serves a
job-bound, already owned native object. Brownfield enumeration has a separate
campaign authority; it must not create a dummy native owner, broaden a site SQL
login or reuse a mutation lease to obtain read access.

The control plane admits a campaign only for an enrolled site worker and an
exact organization, tenant, WSD, site, endpoint, native scope and platform
family. Admission binds a selected installed API/version profile, a read-only
Vault role, a bounded time window, page/object/request budgets, a collection
field set and an issuer/audit identity. Site mTLS and its immutable database
role binding remain required. The worker receives only a one-use wrapped read
credential and makes allowlisted GET requests to its configured management
endpoint. A human bearer token or registration body never supplies an endpoint
URL, credential path or collector result authority.

Campaign, page and snapshot records are append-only. The ingestion boundary
authenticates the site worker, checks the campaign epoch and exact scope, page
sequence and digest, and records collector/API provenance. The site login cannot
write tenant records directly. A new generation becomes **complete** only after
the terminal cursor, all pages, required permission/field coverage and budget
checks pass. An error, changed cursor, duplicate native identity, unsupported
API version, lost permission or timeout produces an explicitly partial/unknown
generation. No partial generation tombstones a previously seen VM or proves
absence. A complete, same-scope generation can record absence while preserving
the native ID and rename history. Names are display attributes, not keys.

Only endpoint-scoped, currently authorized reads expose observations to an
operator. Observation is distinct from the accepted workload binding and from
native ownership. Brownfield adoption produces a reviewed no-change proposal;
an ownership collision, mismatched native identity, unknown source fact or
unaccepted policy dependency holds it. Adoption does not invoke provisioning.

## Comparison semantics

The catalogue keys a directed route by exact source and destination installed
tuples, method, guest, data and network modes. Source export qualification,
destination operation qualification, policy translation and recovery evidence
are independent. Expired or absent evidence is not inferred from a family,
reverse direction or similar version. Assessment reports `ELIGIBLE`,
`CONDITIONAL`, `BLOCKED` or `UNKNOWN`, with each hard constraint, unknown,
remediation and confidence source visible. A comparison is information for a
sysadmin; it never mints a plan approval or starts a native job.

## Delivery and acceptance sequence

1. Implement immutable scope/page/campaign models and a durable generation
   store with exact-scope authorization and change history.
2. Add independently reviewed VMware, AHV and OpenStack GET-only collectors.
   Prove pagination, stable IDs, project/tenant isolation, missing privileges,
   error/timeout handling and installed API compatibility against selected
   native lab environments. Existing exact-ID readback tools can verify a
   selected object; they are not enumeration implementations.
3. Add optional enrichment with source attribution, reviewed application
   grouping and explicit unknown dependencies/consistency groups.
4. Publish a directed, time-bound route ledger and deterministic assessment
   engine. Show observed portfolio and two or more destination comparisons in
   the portal and thin CLI without implying an executable migration.
5. Exercise change reconciliation and an agreed estate benchmark. The plan's
   50,000 workload/100 endpoint target and p95 under two seconds are proposed
   acceptance targets, not achieved measurements.

The Wave 2 repository exit is a working read-only operator path with stable
source identities, scoped generations, blockers, unknowns and remediation.
Native B14–B16 acceptance requires a real installed platform tuple and an
independent inventory comparison; site qualification stays held without it.
