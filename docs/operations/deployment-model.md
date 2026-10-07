# Deployment and operating model

**Status: proposed specification, not an installed topology.** This document develops [architecture sections 5–9](../architecture/target-architecture.md) and [deployment stages D01–D09](../implementation/phased-plan.md). ADR-006 through ADR-012, ADR-016, ADR-017 and ADR-020 resolve the relevant selections. Values marked **selection needed** must become reviewed configuration before their dependent work begins. No native access or production enablement is implied.

## 1. Placement and trust boundaries

The proposed control plane contains the Laravel console, governance/catalogue/assurance services, Python inventory/planning/lifecycle services, Temporal, an event broker, context-owned databases, evidence metadata/object storage and operational telemetry. Use one operated control plane per approved trust/residency boundary. Separate deployments may be required for enclaves, classifications or connectivity constraints; cross-boundary federation is outside initial support until explicitly designed.

Site-local worker pools provide discovery, infrastructure, guest, shared-service and data-movement activities. Discovery has read authority; mutation pools have distinct scoped identities and short-lived execution authority. A task queue is a routing mechanism, not an authorization boundary: a worker validates the admitted job, tenant, endpoint, operation and fencing scope before an effect. Centralized workers are an alternative only after reachability, latency and trust are demonstrated.

| Boundary | Permitted purpose | Prohibited implicit authority | Design and qualification obligation |
| --- | --- | --- | --- |
| Browser to console | Authenticated operator journeys and session management | Browser-held native credentials or direct access to private service databases | CSRF/session handling, authorization and tenant-negative journeys |
| Console to services | Tenant-scoped commands, queries and presentation composition | Tenant headers or network location serving as identity | Validated issuer/audience/principal, delegation and R03/R04 checks |
| Service to service | Owner APIs and published domain facts | Cross-context database writes or events becoming approvals | R02 contracts, outbox/inbox and authoritative decision-time checks |
| Control plane to site | Approved tasks, operation reports and scoped evidence | A worker registration granting unlimited platform access | Enrolment, revocation, scope checks, fencing and partition tests |
| Site to native systems | Exact approved discovery or mutation | Whole-platform credentials reused across tenants/pools by default | API owner permissions and independent outcome observations |
| Source to target data path | Approved datasets and temporary conversion/staging | Workload payload passing through console/event broker | Encrypted transfer, residency, capacity bounds, integrity and disposal |
| Operations/admin plane | Deployment, incident containment and restricted support | Runtime administrator automatically becoming tenant approver | Attributable, time-bounded privilege and separation of duties |

Network segmentation, authenticated channels and application authorization are separate requirements. Kubernetes namespaces alone do not provide tenant isolation. CNI enforcement, east–west denied paths and management access are tested on the selected runtime; declarations alone are insufficient.

## 2. Environment ladder and promotion

| Environment | Permitted work and data | Native mutation boundary | Required promotion evidence |
| --- | --- | --- | --- |
| Development | Synthetic fixtures, component tests and developer dependencies | No production/native credentials; local doubles only by default | Reproducible dependency locks, unit/contract results and image provenance |
| Integration | Real service databases, broker, Temporal, evidence store and simulated platform adapters | Simulator effects only | Cross-language interoperability, isolation, duplicate/lost-message and recovery tests (E2) |
| Native qualification | Isolated commissioned source/target tuples, approved test applications and campaign datasets | Separately authorized lab campaign policy for unqualified candidates | Positive, negative, fault and recovery observations against exact artifacts/tuples (E3) |
| Preproduction | Operated deployment representative of selected production topology; synthetic or explicitly approved data | Only authorized representative test endpoints and scope | Install/upgrade/restore, load/security, alert delivery and receiving-team rehearsal |
| Production pilot/production | Approved tenant workloads and accepted operational controls | Current exact-tuple qualification plus plan-specific authority and change conditions | P10/P11 operational acceptance, support ownership and release-bound scope (E4) |

Build once and promote the same signed application image digests. Record environment-specific configuration separately by non-secret digest and approved secret references. A material code, adapter, infrastructure or configuration change requires qualification impact analysis; using the same image does not prove equivalence of changed infrastructure. Environments use distinct identities, databases, workflow namespaces, broker credentials, evidence scopes and signing/trust policies. No test process obtains production authority through a shared secret or task queue.

## 3. Component and environment bill of materials

P01 must produce a machine-readable environment BOM. The following is its minimum schema expressed as a selection register. Counts, sizes, ports and products are not final until the named decision resolves them.

| Component | Candidate responsibility | Selection needed / recorded BOM fields | Accountable role |
| --- | --- | --- | --- |
| Runtime and ingress | Kubernetes control-plane hosting with enforced network policy and TLS ingress | Distribution/version, CNI, ingress, storage classes, failure domains, scheduling/replica policy, administrative access | SRE/security, ADR-011 |
| Console and business services | Laravel/PHP; console asset pipeline follows directed Inertia/Vue/TypeScript/Tailwind/Vite majors | Resolved runtimes/patches, locks, image digests, health probes, resource requests/limits and migration identity | Product engineering, ADR-002/003/019 |
| Technical services and workers | Python APIs and scoped activity pools | Python/SDK/provider versions, images, worker version-routing policy, queues and execution limits | Infrastructure, ADR-003/007/016 |
| PostgreSQL | Private context databases and separately owned workflow persistence as selected | Version, service/database roles, topology, backup mechanism, encryption, connection and storage limits | SRE, ADR-006/007 |
| Temporal | Durable workflow history and task dispatch | Server/SDK compatibility, persistence/visibility backends, namespace isolation, retention and recovery configuration | SRE/lifecycle, ADR-007 |
| Event transport | At-least-once domain events | Broker/version, HA, queue/topic policy, ordering, retention, replay/dead letters and principal scopes | SRE/architecture, ADR-008 |
| Workload identity, secret and key services | Workload authentication, secret delivery and signing/encryption custody | Provider/version, service audiences, PKI chains, rotation/revocation and recovery dependencies | IAM/security, ADR-009/010 |
| Human authentication | Deployment-created local administrator until console-managed external OIDC activation | Random temporary password displayed once during deployment; mandatory first-login change; Governance connection revision and tested federated administrator before local retirement | Governance/IAM, ADR-009 |
| Evidence object storage | Protected evidence bytes, integrity and retention | S3-compatible endpoint implementation/version, object permissions, retention/immutability mechanism, replication and restore behavior | Assurance/SRE, ADR-010 |
| IaC state | Locked infrastructure state with one owner per field/resource | Tool/provider versions, backend, state encryption, lock/fencing semantics and recovery | Infrastructure, ADR-016 |
| Telemetry and audit | Redacted correlated signals, alerting and protected accountability | Collector/exporter versions, sinks, retention, access, alert routing and dependency health | SRE/security, ADR-017 |
| Artifact supply | Images, packages, charts, guest images and signatures | Registry/mirror, SBOM/signature references, dependency closure and offline-promotion rules | Delivery/security, ADR-020 |
| Native/service endpoints | Selected platform and IPAM/DNS/identity/backup/monitoring APIs | Protected installed tuple references, entitlements, network/storage backend, owners, API budgets and qualification refs | Platform/service owners, ADR-015 |

Each BOM record includes environment ID (synthetic in repository examples), release manifest revision, component version/digest, configuration revision, dependency references, owner role, classification/residency decision and recovery group. Secrets are references only. Record actual resource sizes after the [capacity model](../implementation/estimation-and-dependencies.md) is measured; this plan does not guess production sizing.

## 4. Proposed network and identity flow register

These are logical candidate flows, not firewall approvals. P01 converts selected flows to exact endpoint, port, initiating direction, certificate/identity, authorized scope, timeout/budget, owner and evidence records in the restricted environment register. Do not enable unused optional flows. Platform/guest/storage/data protocols depend on the selected method and tuple.

| Initiator → receiver | Candidate protocol / purpose | Identity and scope | Data and failure behavior |
| --- | --- | --- | --- |
| Browser → console / IdP | HTTPS; local setup login/password change before activation, then OIDC redirects and authenticated sessions | Human principal; mandatory-change state and tenant/role evaluated by owning service | No native credentials; retired local login stays disabled during an IdP outage |
| Console / context service → context API | HTTPS with authenticated service channel | Workload identity plus validated actor delegation; resource/action scope | Versioned commands/queries; fail closed at authorization boundaries |
| Owning context → its PostgreSQL | PostgreSQL over TLS | Distinct runtime role and separately controlled migration role | Private data/outbox/inbox only; no cross-service table access |
| Producers/consumers → broker | TLS-protected selected broker protocol; e.g. AMQP if that broker is selected | Separate publisher/consumer permissions per channel | Tenant-minimal event facts; durable retry/dead-letter and no direct native effect replay |
| Lifecycle / workers → Temporal frontend | gRPC over TLS, subject to selected authentication support | Namespace/pool identities plus application-level admitted scope checks | Workflow/task metadata, not workload disk payload; outages hold unsafe new dispatch |
| Worker → lifecycle API / secret broker | HTTPS or selected authenticated broker API | Enrolled worker, short-lived job authority and scoped secret grants | Ledger attempts/observations and just-in-time credentials; secret/authority failure blocks effect |
| Discovery/infrastructure worker → platform API | HTTPS or selected vendor API protocol with certificate validation | Read-only collector or separately scoped mutation identity | Inventory/control operations under rate limits; uncertain outcomes reconcile before retry |
| Guest worker → selected guest | SSH for selected Linux path; Windows transport requires later selection | Per-job scoped guest credential/certificate | Guest readiness/hardening; disconnection never proves success |
| Shared-service worker → IPAM/DNS/backup/etc. owner | Selected authenticated API; HTTPS proposed where supported | Adapter-specific role limited to admitted objects | Idempotent reservations/receipts; partial completion reconciles through lifecycle |
| Source/target data worker → transfer/staging endpoints | Selected encrypted data-transfer/storage protocol | Dataset/temporary-object scope and key access | Data stays on approved path; integrity, checkpoints, bandwidth and retained-source budget |
| Authorized producer/reader → evidence store | HTTPS S3-compatible object API plus assurance metadata API | Job-bound write scope or authorized reader; distinct retention administration | Digests/custody receipts; missing evidence holds dependent completion/activation |
| Services/workers → telemetry/audit | OTLP over TLS or selected secured exporter | Workload identity, redaction and sink scope | No secrets; buffers/backpressure bounded; mandatory audit failure follows reviewed hold policy |
| Runtime/worker → registry, DNS, time and PKI | HTTPS registry/PKI; approved DNS/time protocols selected per environment | Read artifact role and approved infrastructure trust | Dependency closure/signature checks; unavailable trust/time blocks unsafe admission |

Task polling can make worker-initiated site connectivity practical; callback, guest-access and data paths still need explicit design. Record return paths, NAT, proxies, MTU, overlapping tenant addresses, DNS resolution and failure behavior. Do not assume opening a control API also authorizes disk transfer, guest configuration or workload service traffic.

## 5. Configuration and secret ownership

| Configuration class | Owner and authoritative location | Validation and change rule |
| --- | --- | --- |
| Application defaults and schemas | Owning service in repository | Typed validation; no deployable starts with unknown or invalid mandatory settings |
| Environment topology/limits | SRE-managed deployment configuration | Reviewed non-secret revision; binds BOM, network register and measured resource limits |
| Tenant intent and grants | Catalogue/governance APIs | Revisioned domain changes and authorization; never edited via deployment values |
| External OIDC settings and bootstrap state | Console administration through Governance APIs; controlled deployment bootstrap | Provider/client details and mappings are application data; secrets use protected custody. Random initial password is displayed once, changed at first login and retired with local login after verified OIDC activation |
| Native endpoint/worker enrolment | Inventory/site commissioning with IAM scope | Protected endpoint records and trust bootstrap; no implicit management ownership |
| Profiles, policies and qualification | Planning/assurance | Version/digest binding; changed material inputs invalidate affected plans/claims |
| Credentials and encryption/signing keys | Approved secret/key owner | Out-of-band bootstrap, scoped runtime fetch, rotation/revocation and tested recovery |
| native resource custody and native bindings | Declared state owner plus lifecycle ledger | Locked state, explicit field ownership and recovery reconciliation; no competing API writer |

Run secrets through an approved mounted/in-memory or broker mechanism selected in ADR-010. Do not bake them into images, source, fixtures, evidence or logs. Environment-variable use, if selected, requires exposure/redaction review. Rotation procedures establish overlap, expiry, affected running work and safe continuation; a new credential does not automatically reauthorize an old job.

### Laravel runtime and process contract

Each PHP service publishes its runtime binding: PHP/extension versions, web process model, separate local queue/scheduler processes, startup validation, permitted writable paths, resource/connection budgets, probe behavior and graceful shutdown. Use the [data and messaging standard](../engineering/data-and-messaging.md) for job authority, queue deadlines, tenant isolation and schema evolution. Octane is optional and needs measured benefit plus long-lived request isolation tests before selection.

The web root is Laravel's `public` directory; source/configuration files are unreachable through ingress. Set `APP_DEBUG=false` for production. Grant runtime write access only to approved storage/cache/temp paths and keep credentials out of assets. These follow [Laravel deployment guidance](https://laravel.com/docs/13.x/deployment), reviewed 2026-10-04.

Build immutable images without environment-specific configuration caches. At deployment, supply the selected environment configuration and secrets, validate them, then generate any configuration cache in an access-restricted runtime filesystem. That cache may contain resolved secrets: exclude it from image layers, artifact uploads, diagnostic bundles and logs. Application code reads `config()`; `env()` is confined to configuration files. Environment changes require deliberate cache regeneration and process replacement; editing an external variable cannot update a running process's cached configuration. Test route/event/view caching against the actual application during delivery. [Laravel configuration caching](https://laravel.com/docs/13.x/configuration#configuration-caching)

| Health signal | Purpose and dependency treatment |
| --- | --- |
| Startup | Allow the measured bootstrap/configuration period before normal probes; no migrations or native effects inside the probe |
| Liveness | Detect a locally stuck process. Do not restart every replica because a common database, broker, IdP or native platform is unavailable |
| Readiness | Decide whether this instance can safely serve its assigned traffic, including required schema and bounded essential dependency checks. Keep optional downstream failures scoped to the affected operation |
| Journey/dependency monitoring | Measure actual service operation, backlog/freshness and downstream failures independently of process restart decisions |

Laravel's default `/up` reports successful application boot; it does not prove tenant isolation, schema compatibility or a working native journey. Additional diagnostic checks must not turn liveness into a dependency restart cascade. Probe responses expose minimal status, while detailed diagnostics remain restricted. Kubernetes startup/readiness/liveness semantics inform this project policy; exact timings require installation/load evidence. [Laravel health route](https://laravel.com/docs/13.x/deployment#the-health-route), [Kubernetes probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

Roll HTTP, Laravel job and scheduler processes independently with explicit drain behavior. Stop new consumption/admission to the retiring instance, allow bounded in-flight work to reach the documented safe boundary, and reconcile interrupted work using stable IDs. The process supervisor/orchestrator restarts exited workers with the target image/configuration. Record termination grace, job timeout and redelivery ordering. Changing code on disk does not refresh a running worker. Do not use broad cache-clearing commands to coordinate deployment; locks, sessions and durable queues have separate loss policies.

### Application encryption key lifecycle

Provision an independent Laravel application key per service/environment, consistent across replicas of that service. Do not generate a new `APP_KEY` on every boot or reuse one across all contexts. ADR-010 records custody, recovery and rotation authority separately from native credentials and evidence signing keys.

Laravel supports previous decryption keys through `APP_PREVIOUS_KEYS`. For planned rotation, first make the new key readable by every continuing/rollback-compatible instance while retaining the existing encryption key; then promote the new key for encryption while retaining the old decryption key. Regenerate protected configuration caches and replace all affected processes at each stage. Test old/new cookies, encrypted records and encrypted jobs across the mixed-version window. [Laravel key rotation](https://laravel.com/docs/13.x/encryption#gracefully-rotating-encryption-keys), reviewed 2026-10-04.

Inventory retained ciphertext, queued payloads and backup recovery requirements before retiring a key. Re-encrypt or retain protected decryption access according to policy; a key list does not automatically rewrite stored data. A suspected compromise follows the incident decision on revocation, forced reauthentication and recovery instead of automatically preserving a compromised key for continuity. Restore tests must include the key versions needed by their recovery points.

## 6. Installation readiness and evidence

Apply D01–D09 in the phased plan as the authoritative sequence. Before progressing each stage, attach its evidence to the associated work package and campaign. This table adds the operational checks that make that sequence reviewable.

| Readiness boundary | Checks and required evidence | Hold condition |
| --- | --- | --- |
| Before dependencies | Approved hosting/residency, capacity/failure domains, DNS/time/trust, artifact closure, identities and recovery owners | Missing mandatory dependency, ownership or authority |
| Before application services | Exact BOM, least-privilege persistence, encryption, healthy broker/workflow/object dependencies and exercised integration restore | Unrestorable required state or unresolved credential/contract incompatibility |
| Before worker enrolment | Signed matching artifact, endpoint trust, distinct pool permissions, queues, budgets, revocation and allow/deny flows | Untrusted endpoint, overbroad credential or routing without authorization |
| Before native qualification writes | P06 safety results, commissioned isolated tuple, approved campaign/plan, reconciled reservations, stop/recovery controls and evidence path | Missing campaign authority, unknown native state, stale required input or unsafe recovery |
| Before supported operation | Current exact-tuple native qualification, supported release/configuration, operational runbooks, alert receipt and accepted service dependencies | Empty/expired/revoked qualification or unsupported tuple/method |
| Before pilot acceptance | Measured targets, operator-led install/recovery, application checks, security/service-owner acceptance and bounded support publication | Unresolved mandatory gate or evidence mismatch to release artifacts |

Store commands, expected outputs and actual redacted observations in future executable installation/runbook artifacts. This specification provides no installation pass or evidence receipt.

## 7. Backup, restore and native consistency

Recovery scope includes each context database (including outbox/inbox and operation ledger), Temporal persistence and required visibility data, broker retention/replay state, evidence bytes/metadata, infrastructure state, deployment/configuration manifests, trust/identity dependencies and encryption keys. An operational backup catalogue records owner, consistency boundary, retention, location, restore dependency and measured RPO/RTO for each. Candidate targets in the phased plan need owner acceptance; application data objectives remain separate.

A single atomic backup across these systems is not assumed. Select coordinated checkpoints or recoverable watermarks and document the resulting cross-system reconciliation rules. Keep evidence objects immutable where selected; compare metadata references and digests after restore. A broker replay window or Temporal history beyond the restored lifecycle ledger must not recreate authorization or cause duplicate native operations.

Recovery procedure design must establish this order:

1. Contain new admission and isolate restored workers from native mutation paths; revoke/fence old execution authority through mechanisms that prevent an old partitioned worker continuing writes.
2. Restore required identities/keys/trust and persistent systems into an isolated environment at recorded recovery points. Keep dispatch and mutating workers disabled.
3. Reconcile database/outbox/inbox watermarks, Temporal histories, job/operation records, broker events, evidence objects and native API/native bindings. Report gaps rather than inventing missing success records.
4. Independently observe native operations that may have completed after the recovery point. Classify every affected operation as known-not-started, confirmed failure, confirmed success or outcome unknown. Unknown effects remain held.
5. Revalidate current grants, revocations, qualification, plan freshness, reservations and resource ownership; old approvals and restored leases are not current authority. Establish a new effective fencing epoch before enabling writes.
6. Resume only reviewed compatible workflows, reconstruct safe projections and verify application/service checks. Release admission gradually under operator observation and preserve the incident/evidence record.

The exact containment/fencing mechanism is a P06 design dependency and native gate; merely changing a database epoch is insufficient if an old worker can still reach a platform with valid credentials. Recovery tests include loss of a site, partial object restore, lost key access, stale approvals, ambiguous native completion and divergent source/target application data. Restoring control-plane state never justifies discarding target writes by turning the old source back on.

## 8. Upgrade and downgrade semantics

Each release publishes service/API/event/schema compatibility, database migration stages, Temporal server/SDK/worker constraints, adapter/profile revisions, configuration changes and affected qualification. Expand/contract migrations preserve the stated mixed-version window; destructive contraction waits until old readers/workers and retention obligations no longer require the old shape.

Running workflows route to compatible workers under the selected Temporal versioning strategy. Replaying historical workflow code or deploying a new activity implementation is not presumed safe. Test old/new worker coexistence, pinned long-running workflows, mixed contract versions, rollback before contraction and interrupted upgrades in Q09.

An application image rollback does not reverse a database migration, native mutation or completed cutover. The release specifies when rollback is possible and when forward repair or isolated restore is required. Before upgrade, stop or bound affected new admissions, retain recovery material, verify artifact trust and exercise the selected path in preproduction. Post-upgrade checks compare native job states, evidence custody, tenant isolation and critical operator journeys. Changed adapter behavior or materially changed environment tuples triggers scoped requalification before advertising continued support.

## 9. Restricted and disconnected environments

ADR-020 decides whether restricted-network installation is in the first release. If selected, mirror the complete build/runtime dependency closure, signed images/charts, guest artifacts and trust metadata; record provenance and test installation with public internet blocked. Approved update import/export and retention procedures are part of the environment BOM.

Disconnected execution is a separate capability. Default behavior holds new unsafe work when current authority, reservation renewal, ledger/evidence custody or native observations cannot be established. Any permitted continuation requires an explicit bounded policy with authority expiry, safe points, durable local observations and tested reconnection reconciliation. An offline package alone proves none of those execution properties.
