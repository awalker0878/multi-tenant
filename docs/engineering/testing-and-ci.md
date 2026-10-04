# Testing, continuous integration and verification

Owner: quality lead with engineering, security and SRE. Reviewed: 2026-10-04. Applies from P01 to the six business services, console and site workers. P01.03 establishes contract/messaging checks; P01.04 implements the pipeline. The [qualification campaigns](../qualification/README.md) and [gate criteria](../implementation/gates.md) define the later evidence needed for admission and support.

This standard connects everyday developer feedback with enterprise failure cases. Tests are selected by behavior and risk, not file counts. A documentation check, formatter result, unit suite or successful image build cannot establish native-platform qualification.

## Test ownership and environment levels

Each service owns tests of its behavior and persistence. Producers own API/event conformance; consumers own their expectations and compatibility checks. The quality lead owns the integrated critical journeys; security reviews denial coverage; SRE owns deployment and recovery verification. The [context inventory](../../architecture/context-map.yaml) supplies declared ownership and dependencies. P01 binds its entries to actual source/build/contract artifacts and named suite entrypoints so CI selection is reproducible. The [code-control policy](code-control.md) defines architecture checks, required review and merge admission.

Laravel supports focused unit tests and framework feature tests; units do not automatically boot the application. Prefer feature tests for actual HTTP, validation, policy and database behavior, while pure algorithms and value objects stay fast and isolated [T1]. Python services follow the same boundary principle. These suite categories complement the E0–E4 [evidence model](../implementation/status-model.md); a test's location or name does not assign its evidence level.

| Test boundary | Required environment | What it can establish |
| --- | --- | --- |
| Pure rules and transforms | In-process inputs with controlled clocks/randomness | Domain invariants, parsers, digests and decision logic |
| Laravel/Python service behavior | Real application, production-family PostgreSQL for persistence cases; isolated dependencies | HTTP/policy/validation, transactions, queries and ownership within the service |
| Contract and transport integration | Actual producer/consumer builds, locked schemas, real PostgreSQL and selected broker | Cross-language interpretation, compatibility, outbox/inbox and delivery behavior |
| Browser and identity integration | Built console, actual receiving services and selected isolated issuer/session system | User task, cookie/request-forgery controls, delegation and accessibility behavior |
| Workflow integration and replay | Compatible Temporal test/server environment, actual worker code and controlled activities | Timers, cancellation, workflow history compatibility and worker recovery |
| Deployment, resilience and native qualification | Exact isolated deployment or authorized native tuple | The scoped installation/recovery/native outcomes in the campaign; never inferred from mocks |

SQLite and array/synchronous drivers may support narrow feedback loops. They do not replace PostgreSQL constraints/locking, shared cache/session behavior, broker redelivery or long-running workers when those are the subject of the assertion. Laravel database transaction helpers are useful for test isolation; tests of actual commit visibility, `after_commit` dispatch and concurrent connections need a separately reset real-commit environment [T2].

## Architecture verification is a distinct suite

Mirror production context/layer boundaries in test ownership. Domain tests use plain values and owned types without booting Laravel, persistence, broker or Temporal. Application tests exercise use cases through owned ports. Infrastructure tests prove the actual adapter contract against isolated dependencies. Interfaces tests prove authenticated transport, validation and application invocation. Cross-service tests use published contracts; test setup must not import another service's private ORM model to seed its database.

P01 proves parser-aware PHP/Python/frontend boundary configuration using legal and violating fixtures described in [code control](code-control.md). Required failures include Domain-to-framework, Application-to-Infrastructure, Interfaces-to-Infrastructure, sibling-service imports, frontend private-module imports and unknown first-party roots. Include qualified/aliased references, re-exports and deleted dependency edges. An always-failing checker does not satisfy this suite: legal examples must pass and illegal examples must report the intended rule.

The current `python scripts/validate_architecture.py` checks the registry and supported source forms, with validator fixtures in `tests/documentation/test_architecture_controls.py`. Its PHP prechecks are conservative; parser-aware Deptrac and supplemental architecture rules remain P01 implementation work. Reports must distinguish a validated registry, analyzed source and absent application code. Registry success is not application security or isolation evidence.

## Minimum behavioral matrix

For each changed surface, identify applicable rows and link the tests to the corresponding requirement or gate criterion. Record a reason when a row does not apply. The matrix is a design obligation, not a claim that the suites already exist.

| Area / principal owners | Required cases | Independent observations |
| --- | --- | --- |
| Authority and tenancy / every service, Q01 | Tenant A identity with B identifiers; forged tenant/actor; wrong issuer/audience; expired/revoked delegation; resource/action scope; direct service request bypassing console | No foreign records, counts, object URLs, cached values or mutations; attributable denial; denial cannot be converted into an event-driven grant |
| Browser and sessions / console + governance | Tenant switching; login/logout/session rotation; stale membership; actual origin/token request-forgery defenses; hostile return URL; permission changes while page remains open | Cookies and actual HTTP results, cleared tenant state, no sensitive browser-history/shared-prop leak; receiving service rechecks authority |
| Domain intent / catalogue | Invalid cross-tenant association, dangling reference, dependency cycle, immutable revision modification, concurrent ETag updates, retry with changed payload | Correct revision chain, one accepted logical mutation, transaction rollback, no stale intent admitted |
| Approvals / governance | Exact digest/revision/action scope, expiry and revocation; requester self-approval; concurrent approve/revoke/admit; restricted break-glass path if selected | Auditable actor and decision, admission consistency, no unrestricted administrator shortcut |
| Inventory and planning / Python owners | Partial/stale observation, malformed/untrusted adapter data, pagination, unsupported capability tuple, deterministic assessment and plan digest | Source/freshness retained, explicit uncertainty, reproducible plan, unsupported route rejected |
| Persistence / every data owner | Tenant-aware uniqueness/foreign keys, lost update, concurrent idempotency claims, deadlock retry, runtime-role isolation, JSON/timezone/serialization edge cases | Real PostgreSQL results across independent connections; no cross-service SQL access; no duplicate logical effect |
| Outbox/inbox / producers and consumers | Failure before commit; relay crash after publish/before acknowledgement; consumer crash after local commit/before acknowledgement; duplicate and out-of-order delivery; poison input; broker unavailable | Mutation/outbox atomicity, eventual recoverable delivery, one logical consumer effect, bounded retry/quarantine and alerting |
| Laravel background jobs / PHP owners | Enqueue/commit ordering; worker termination; timeout and redelivery; stale model/reference; failed-job retry authorization; alternating A/B jobs in one process | Tenant context cleared between jobs, current scoped authority, no escaped secret/session state, idempotent local effects |
| Lifecycle / Python + Temporal | Workflow start ambiguity; timeout after possible native write; retry/cancel/heartbeat; worker crash; revoked execution grant; stale fencing token | One admitted logical job, durable uncertainty, effective fencing and reconciliation before any repeat native effect |
| Evidence / assurance | Wrong tenant/download audience, tampered object/digest, retention/legal-hold constraints, missing object, partial upload and recovery | Authorized access only, verified immutable reference, explicit incomplete evidence, no qualification promotion from missing bytes |
| Console tasks / frontend + APIs | Loading/empty/error/conflict/held/unknown states; duplicate submit; keyboard/focus recovery; responsive layout; supported browser task; screen-reader labels/status changes | Correct visible state, no misleading success, accessible task completion and understandable recovery path |
| Operability / SRE + service owners | Dependency outage, queue lag, pool exhaustion, readiness vs liveness, resource limits, upgrade under old/new versions, schema expansion, failed rollout, restore | Bounded degradation, usable alert/correlation, no leaked secrets, state preserved and recovery constraints honored |

Use [security and tenancy](security-and-tenancy.md) for the threat and surface-specific obligations. Run request-forgery cases with the actual protection enabled: the convenience of Laravel's test environment can bypass middleware behavior, so a passing ordinary feature request is insufficient [T3]. Validate both the selected origin policy and token fallback; do not assert a universal status code across different protection configurations.

## Fakes, fixtures and isolation

Use a fake to isolate a collaborator whose behavior is outside the assertion. Test the real collaborator separately, then cover the integration boundary. `Queue::fake`, `Event::fake`, a mocked authorization check or an always-successful adapter cannot establish delivery, policy enforcement or native safety. Prefer narrow scoped fakes so observers or events needed by the behavior still execute.

Test data uses synthetic identities and at least two tenants where isolation matters. Build factories with explicit ownership relationships and both allowed and forbidden combinations. Do not create one global administrator fixture that accidentally bypasses all policy tests. Fixtures are versioned against source schemas and never seed a production default account or relaxed policy.

Every run and parallel worker receives distinct database names, object prefixes, cache/session namespaces, broker queues/subscriptions, workflow IDs/task queues and port allocations as applicable. Laravel isolates its configured primary test database for parallel workers; that does not automatically isolate all additional dependencies [T1]. Limit test identities to their run's resources and block production endpoints. Cleanup must verify the owned resource prefix before deletion, including after failure.

Reset mutable container singletons, clocks, locale/timezone, tenant context and test doubles between cases. Use deterministic seeds and record a failed randomized case's seed. Control time without real sleeps where possible. Concurrency tests coordinate barriers/acknowledgements instead of relying on a lucky scheduling delay. Run selected tests in changed order to expose hidden dependencies when shared-state defects are suspected.

For a real broker suite, assert durable before/after state and the observable event envelope, not only the mocked publisher call. Include relay and consumer process termination points. The outbox dispatcher, inbox transaction and schema-version handling are separate assertions; success in one cannot hide failure in another.

## Workflow replay and native effects

Lifecycle workflow changes replay a representative versioned corpus covering in-progress and completed histories of every affected workflow type. Fail the compatibility check on nondeterminism. Include the selected worker versioning/migration policy and the supported active-history window in the release review. Temporal's Python test suite provides time-skipping environments and replay facilities; replay checks deterministic history compatibility [T4].

Replay does not rerun activities to prove provider behavior, exactly-once native effects or safe failover. Verify activities, receipts, idempotency and fencing through separate real-dependency and authorized native fault cases. Keep privileged I/O out of deterministic workflow code. Test ambiguous starts and outcomes explicitly; do not turn a timeout into an assumed failure and blind retry.

Use synthetic histories for ordinary CI. If operational histories are needed, obtain authorized access, protect their payloads and preserve replay validity during sanitization; store sensitive history outside the repository. Time skipping is shared within a Temporal test environment, so isolate tests requiring different clock behavior [T4].

## Change-to-check selection

The fast pull-request path runs affected service checks and expands through declared dependency and contract consumers in both the base and proposed inventories. Selection is tested against known change fixtures, including renames and deletions, and fails conservatively when dependency classification is unknown. A required aggregate result must report incomplete, cancelled, stale or failed constituent checks rather than treating a skipped job as a pass. Record why a suite is inapplicable; do not use a successful empty matrix as admission evidence.

| Change | Required scope |
| --- | --- |
| Documentation only | Documentation generation/validation; architecture registry validation when referenced; technical review of changed assertions |
| Context inventory, ownership map, analyzer rules or source layout | Complete architecture/ownership checks and negative fixtures; all affected builds; independent policy review; inspect both old and new dependency edges |
| One context/service implementation | Owning context boundaries and full service lint/types/unit/feature suites, relevant real-dependency integration and affected contracts |
| Schema, generated client or shared technical package | Producer and every direct/transitive consumer build/typecheck/contract suite; integrated affected journeys |
| Authorization, tenancy, shared HTTP middleware, session or evidence policy | All affected service denial cases, full critical isolation suite and relevant browser/identity integration |
| Composer/Python/frontend lock, runtime, base image, shared CI or build tool | Every affected build plus the full critical cross-service suite; all services when shared runtime/tooling changes; advisory/license/BOM review |
| Database schema, broker settings, queue/outbox or workflow code | Real database/transport faults, mixed-version contract checks and affected replay/restart/upgrade cases |
| Deployment topology, credentials, routing, signing or recovery procedure | Isolated deployment/security/rollback checks and affected campaign impact review |
| Release candidate | All required suites against the selected artifact set; exact support-tuple campaign evidence and release-readiness review |

The **critical cross-service suite** covers login/delegation and tenant isolation; application revision to exact-plan approval; admitted job and idempotent dispatch; workflow uncertainty/recovery; and scoped evidence access. It uses actual services and dependency configurations, with only native boundaries simulated until an authorized campaign runs. Add the first native provisioning/migration journey once that tuple is available. Always describe simulation boundaries in results.

Run complete integration regressions on the protected integration branch and release candidates; periodic full runs catch drift and omitted dependency edges. Expensive native campaigns follow qualification impact and lab authorization. They cannot be quietly removed from a release gate because routine PR tests are fast.

## Required pipeline outcomes

P01 implements these jobs using verified commands and locked tools; this document does not introduce working CI configuration.

1. Validate documentation, the ownership/dependency inventory, contracts and deterministic generated-client drift. Execute the pinned language-aware architecture tools: no sibling-service runtime import, no shared private ORM/domain model, no forbidden layer dependency and no hidden runtime bootstrap from legacy code. Fail unknown/unclassified source, unexpected empty scans and unapproved exclusion growth. Run negative tool fixtures whenever rules, parser versions or source discovery change. Database/network role denial tests complement static import checks.
2. Run the service's pinned formatter/linter and type/static analyzer under the [developer standard](developer-workflow.md). Validate manifest/lock consistency, dependency advisories, secrets and licenses; compare suppression and policy baselines with the reviewed base. Reject expired exceptions or silent baseline expansion. A clean static scan is one signal, not proof of authorization correctness.
3. Run risk-selected test suites and produce machine-readable results with counts, failures, skipped/quarantined cases, environment/tool versions, source revision and fixture/schema identities. Keep sensitive payloads out of logs and reports.
4. Build independently from locks and immutable base inputs. Exercise application boot and optimized production configuration in the built image, including route/config caching where supported by the selected runtime. Check actual platform requirements, health and least-privileged runtime behavior.
5. Produce the SBOM, image digest and provenance linking source revision, build definition and inputs. Sign and verify through the selected trust policy, then promote the same tested digest. Provenance verification includes the allowed builder/source identity; a valid signature alone does not establish an approved build.
6. Evaluate the complete required aggregate, current revision/role reviews and scoped exceptions before merge/promotion. Prove failed or missing checks and insufficient review block admission under the selected repository rules. Changes to the gate or workflow itself require trusted-base enforcement and independent review under [code control](code-control.md). Release jobs consume immutable evidence references and the [release manifest](../releases/release-manifest.md); they do not rebuild an allegedly identical release with fresh dependencies.

GitHub Actions uses minimal token permissions, full commit SHA pins for actions/reusable workflows, and separate untrusted PR test and privileged release contexts. Never checkout or execute untrusted PR code with release credentials under `pull_request_target` or an equivalent privileged workflow. Treat upstream artifacts and caches as untrusted inputs unless verified; isolate runners and cache permissions accordingly. Pass untrusted metadata as data rather than interpolating it into shell code [T5].

No PR test job receives production infrastructure credentials. Use short-lived, audience/scope-bound workload identity for a protected release job when supported. Restricted-network builds consume reviewed mirrors with known freshness. Signing credentials, secrets and raw native evidence do not enter general test artifacts.

## Coverage, failures and evidence

Use coverage to find unexercised behavior, especially permission branches, state transitions and exception paths. Review assertions and important negative cases; an arbitrary repository-wide percentage is not a release criterion. Establish measured per-service trends and justified thresholds after useful suites exist. Targeted mutation testing or seeded faults can test whether safety-critical assertions actually detect a defect; do not add assertion-free tests to raise a metric.

A flaky test is a defect with an owner, reproducer and deadline. Retrying to diagnose is allowed; present the original failure and retry outcome. Quarantine requires a reviewed scoped exception and a compensating check; required authority, isolation, fencing or data-integrity acceptance does not silently become optional. Test results must distinguish skipped, inconclusive and failed from passed.

Store actual evidence in the authorized system and link immutable references through the [delivery register](../implementation/delivery-register.yaml). Include source/artifact versions, executed case IDs, dependency/configuration tuple, observation time, failures, limits and reviewer where required. Keep documentation verification and application/native results separate. Updating this standard does not advance delivery or qualification status.

## Standards and primary references

Reviewed 2026-10-04. NIST SSDF 1.1 is the published final SP 800-218 baseline; the 1.2 revision page is an initial public draft at review time. SLSA 1.2 is an approved specification. Use their secure development and supply-chain practices to structure controls; no SSDF compliance, SLSA level or independent certification is asserted by this document [T6, T7].

| Ref | Primary source | Application |
| --- | --- | --- |
| T1 | [Laravel 13 testing](https://laravel.com/docs/13.x/testing) | Unit/feature boundaries, environments and parallel tests |
| T2 | [Laravel 13 database testing](https://laravel.com/docs/13.x/database-testing) | Persistence fixtures and test transaction isolation |
| T3 | [Laravel 13 HTTP tests](https://laravel.com/docs/13.x/http-tests) and [request forgery protection](https://laravel.com/docs/13.x/csrf) | Explicit protection tests beyond ordinary test-mode requests |
| T4 | [Temporal Python testing](https://docs.temporal.io/develop/python/best-practices/testing-suite) | Activity/workflow tests, clock isolation and history replay |
| T5 | [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use) | Action pins, least privilege, untrusted code and script-injection boundaries |
| T6 | [NIST SSDF 1.1 final](https://csrc.nist.gov/pubs/sp/800/218/final) and [SSDF 1.2 initial public draft](https://csrc.nist.gov/pubs/sp/800/218/r1/ipd) | Distinguish published baseline from draft evolution |
| T7 | [SLSA 1.2 specification](https://slsa.dev/spec/v1.2/) | Versioned provenance/build assurance reference; level claims require separate assessment |
