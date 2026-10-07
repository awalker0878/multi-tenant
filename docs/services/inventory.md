# Inventory service

Status: P01 independently packaged service and owned worker foundations are implemented; the discovery, observation and collection behavior specified below remains planned. Runtime: Python; source: `services/inventory/` and `workers/inventory/`. Owner: infrastructure engineering with site/platform owners.

The [service package](../../services/inventory/README.md) and [Inventory-owned worker package](../../workers/inventory/README.md) each have a private manifest, dependency lock, wheel and diagnostic entrypoint. `inventory-health` and `inventory-worker-health` implement one-shot process liveness only. Readiness deliberately exits unavailable; the worker declares task consumption disabled. No HTTP API, discovery request, endpoint collection, persistence or other business behavior is implemented, and neither package performs native operations.

The [Python package report](../implementation/p01-python-foundations.md) records independent installations and isolated wheel execution. The [Python image report](../implementation/p01-image-foundations.md) records the actual restricted container builds and diagnostics. These results establish bootstrap boundaries, not discovery readiness or a running collector.

## Purpose and responsibility boundary

Provide trustworthy, sourced observations of sites, endpoints, platform versions, resources and capacity. Record what was seen, by which authorized collector, with which coverage and at what time so planning can distinguish fresh facts, partial results and unknowns.

Inventory does not acquire native ownership, reserve observed capacity, issue write credentials or commission a site for mutation merely by registering an endpoint. It does not infer support from a platform brand or declare missing resources deleted after an incomplete scan.

## Owned aggregates and invariants

| Aggregate | Rule |
| --- | --- |
| Site / Endpoint | Registration, owner, approved connection/trust parameters, scope and credential reference; secrets remain in their owning service. |
| CollectionRequest / generation | Stable task ID, endpoint/collector versions, authorization scope, start/end, pagination and completeness result. |
| Observation / observed resource | Immutable source facts with native identity, endpoint identity/epoch, collection time, expiry and provenance. |
| Observed DomainInstance | Native realization of a logical domain with observed routing/enforcement properties; managed binding remains lifecycle-owned. |
| Commissioning record | Collected site facts and references to owner/assurance acceptance; registration, discovery readiness and approved write readiness are distinct. |
| Tombstone / identity exception | Explicit completed-generation evidence of disappearance, or unresolved ID collision/reuse; no silent reassignment. |

Endpoint-native ID alone is not globally unique. Preserve endpoint identity and generation/reinstallation evidence; ambiguous reuse creates a hold. Logical tenant visibility is an authorized mapping, not inferred from a native name. Cross-tenant shared-resource facts require a redacted authorized view that does not expose other workloads.

## Proposed API surface

Routes use `/v1/tenants/{tenant_id}` for tenant views. Estate/site administration, if required, has separately scoped contracts rather than a wildcard tenant bypass.

| Method and route | Contract |
| --- | --- |
| `POST /sites` / `POST /sites/{id}/endpoints` | Register approved location/endpoint and secret reference using idempotency; validate allowlisted destinations and trust before collection. |
| `POST /endpoints/{id}/discoveries` | Enqueue bounded read-only collection; `202` with discovery ID and status URL; no lifecycle native-write authority. |
| `GET /discoveries/{id}` | Task status, coverage, failures and generation references; partial completion cannot claim full coverage. |
| `GET /observation-generations/{id}` | Immutable generation metadata and authorized resource pages with consistent snapshot cursor. |
| `GET /resources/{id}` | Latest observation plus source generation, freshness, completeness and identity exceptions; never imply ownership. |
| `GET /sites/{id}/readiness` | Separate registered/discovery-ready/commissioning-accepted facts and explicit blockers with authoritative references. |

Worker submission is a private authenticated collection contract bound to endpoint, tenant scope, task/generation and collector artifact. Reported endpoint/resource IDs are checked against enrollment; a collector cannot reassign an observation to an arbitrary tenant.

## Authorization and bootstrap

Governance controls endpoint administration and `inventory.discovery/read` scopes. Enrollment validates site owner approval, worker identity, allowed hosts/protocols and the exact read-only credential scope. Client-submitted URLs cannot turn collection into an arbitrary internal network probe; resolve and validate destinations using the approved endpoint policy.

P04 can start only with P02 trust interfaces and P01 isolated runtime. Selected actual OpenStack and VMware endpoints are required for P04 native read-only acceptance. Simulated records remain visibly synthetic and cannot satisfy site commissioning.

## Consistency, retries and events

A collection idempotency key binds endpoint, requested scope and collector/profile version. Persist task creation and dispatch outbox together. Page retries deduplicate by task/page/source identity, retaining provenance. Publish a complete generation pointer only after all mandatory pages/checks finish; failed mandatory coverage produces partial/failed status, not a fresh full snapshot.

Use expected configuration revision for endpoint edits. A revoked enrollment or changed endpoint scope blocks further accepted submissions according to the trust policy. Late worker results are retained/rejected with provenance and must not become a current generation silently.

Publish `inventory.discovery.completed`, `inventory.observation-generation.published` and `inventory.endpoint.changed`; include coverage/freshness metadata. Consume governance revocation for prompt collector/cache updates, but directly revalidate enrollment/authority before dispatch and result acceptance. Events signal change; planning pins the full authorized generation from inventory.

## Dependencies and failure behavior

Dependencies: governance, secrets/trust, endpoint connectivity, inventory database and dispatch transport. Native timeouts, rate limits, permission truncation and inconsistent pages are observable failures. Retrying collection uses bounded backoff and budgets; API responses remain read-only. An endpoint outage expires readiness and observations; it does not cause destructive cleanup elsewhere.

Observed capacity is informational. Lifecycle makes any approved reservation against the authoritative owner and reconciles it; inventory never grants a reservation by decrementing its cached count. Site acceptance references are checked again by admission, avoiding an inventory/assurance event projection becoming an independent write permit.

## Deployment and operation

Deploy collectors independently by site/trust boundary with native read-only credentials, endpoint allowlists and bounded concurrent requests. API and collection workers share only inventory-owned persistence/contracts. Collection pools do not carry infrastructure mutation credentials.

Measure freshness, complete-generation age, pagination/permission gaps, endpoint throttling, collection backlog, identity collisions and per-tenant fairness. Preserve clocks and provenance; retention/downsampling may remove detail only under an explicit policy that does not invalidate referenced plans/evidence silently. Restore restarts collection cautiously and does not present restored old observations as freshly observed.

## Verification and delivery

P04.01 site enrollment; P04.02 collectors; P04.03 observation store; P04.04 budgets; P04.05 console experience. Later P09 adoption uses these facts but requires separate lifecycle ownership transfer. Requirements R04/R08–R11/R34; Q02 and Q03.

Test partial page sets, hidden permissions, rate-limited endpoints, stale clocks, native ID reuse, tenant mapping errors, revoked/forged collector, late results, collector restart, outbox retry and incomplete-scan deletion. Independently observe that P04 collection makes no native changes and cannot receive write credentials.

## Context source ownership and code control

P08 adds immutable workload profiles and administrator migration reviews under
[Inventory v1.2](../../contracts/openapi/inventory-v1.2.json). The scoped leased
collector authorizes and budgets every profile read, and publishes only a complete
generation. Review revisions separate observed API facts from complete dataset maps,
explicit method, owner-only references/objectives and reasoned interpretations.
Confirmation rechecks profile freshness and authority and grants no native write.
Planning alone reads the exact confirmed migration input through its authenticated
owner route; stale generations, scope mismatches and revoked policies remain held.
See the [P08 record](../implementation/p08-execution.md) for qualified boundaries.

Owned source root: `services/inventory/src/inventory/`. Site/endpoint registration, observed resource identity, collection provenance and freshness capabilities. Platform collectors are Infrastructure adapters under inventory authority.

Use the [context code structure](../architecture/context-code-structure.md), [context registry](../../architecture/context-map.yaml) and [code-control policy](../engineering/code-control.md). This Python service retains `domain/`, `application/`, `infrastructure/` and `interfaces/` with the documented dependency direction. Its capability modules may collaborate within the same owning context. Composition binds adapters; public API/event schemas define cross-service access. Internal models, use cases and migrations are not exported as shared business packages. The pragmatic Laravel convention in ADR-024 applies to PHP services and does not relocate this Python source.

The service owner reviews source/dependency changes and maintains legal/forbidden import fixtures, contract consumers and isolated build inputs. Runtime data-access denials remain separate tests. Registration or a static check does not grant a worker additional native authority.
