# Phased enterprise implementation plan

Date: 2026-10-04. Status: proposed implementation baseline. Branch: `greenfield/enterprise-microservices-plan`.

## 1. Outcome, scope and reset

Build a new enterprise control plane for portable hosting and workload mobility. Operators must be able to register an application, describe its security and service requirements, discover approved infrastructure, compare eligible destinations, review an immutable plan, obtain approval, execute through scoped workers and examine independently verifiable outcomes.

The later greenfield direction in the supplied transcript is authoritative. Earlier suggestions to put Laravel over the old APIs, wrap old modules as services or transfer old database ownership are superseded. The previous implementation supplies domain knowledge and scenarios only. Reuse of any small algorithm, adapter idea or test scenario requires review and implementation against the new contracts; no bulk copying of the old runtime, database, configuration or tests as proof of correctness.

This delivery creates the plan and clean branch. It does not implement the phases. Every phase below begins as **planned**.

### First release boundary

The first supported release should operate a deliberately bounded application path, while its product model and contracts represent the complete intended platform scope.

| Dimension | Initial proposal | Expansion or selection rule |
| --- | --- | --- |
| Hosting | Fresh control plane and newly commissioned site workers | No dependency on previous runtime or live state |
| Product users | Platform administrator, tenant administrator, application owner, planner/operator, approver, auditor and service operator | Separate permissions and separation of duties; no role name implicitly grants every action |
| Provisioning | One selected OpenStack installation and one approved Linux guest profile | Exact platform, network, storage and guest versions selected in P00 |
| Migration | One VMware-to-OpenStack offline application route | Prefer cold guest/disk conversion and import if P00 feasibility succeeds; rebuild/restore is a separately named method, never equivalent proof |
| Application | A small multi-workload application with a real stateful component, declared dependencies and explicit security boundaries | Freeze dataset, correctness checks, downtime window and recovery procedure before native testing |
| Services | Real IPAM/DNS, identity, backup and observability paths needed by that application | Choose actual owners and interfaces in P00; simulated substitutes cannot satisfy a native gate |
| Platform breadth | VMware, Nutanix and OpenStack represented by full capability dimensions and explicit unsupported/unknown states | Qualify additional tuples independently in P09 |
| Exclusions from initial support | Live migration, universal guest conversion, automatic cross-platform policy equivalence, arbitrary disconnected operation and all platform/version combinations | Each remains visible in the backlog and unsupported until specifically qualified |

The programme distinguishes deploying a greenfield product from adopting brownfield infrastructure. The new product may later manage existing resources, but adoption requires discovery, ownership proof, drift review and explicit authority before writes. It does not require converting the old application's database.

## 2. Delivery rules and accountable owners

Use the [target architecture](../architecture/target-architecture.md) for boundaries and the [requirements matrix](requirements-and-qualification.md) for coverage. Assign actual people to these role owners in P00; the table does not imply staffing is already available.

| Owner role | Accountability |
| --- | --- |
| Product lead | Personas, scope, application acceptance and release priorities |
| Architecture lead | Contexts, ownership, ADRs, portability and dependency control |
| Product engineering lead | Laravel services, console, domain behavior and usability |
| Infrastructure engineering lead | Python services, adapters, workflows and native execution |
| Platform/SRE lead | Build/release system, runtime platform, observability, recovery and support |
| Security/IAM lead | Trust boundaries, access controls, credential handling and security evidence |
| Quality/qualification lead | Independent acceptance campaigns, traceability and support matrix |
| Platform and service owners | Lab access, authoritative APIs, native configuration and operational acceptance |

Every work package must produce: reviewed code/configuration where applicable; owned contracts and migrations; meaningful tests; operational documentation; a versioned evidence record; and explicit unsupported cases. Small commits should each describe a coherent change. Update the architecture and progress records in the same delivery as a changed boundary or behavior.

Status progression is `planned → in progress → implemented → verified → qualified → accepted`, with `blocked` available at any stage. Verification must name its environment. A phase closes only when its gate is met or its scope is formally narrowed; unfinished work never becomes complete through a waiver that silently broadens support.

## 3. Phase sequence and dependencies

Duration ranges are planning estimates in elapsed working weeks for the named workstream after prerequisites. They are not commitments or additive staffing estimates. Lab access, dependency resolution and service-owner participation can dominate the schedule.

| Phase | Outcome | Entry dependency | Estimate | Accountable lead |
| --- | --- | --- | --- | --- |
| P00 | Product, architecture and qualification baseline | This planning branch | 2–3 weeks | Product + architecture |
| P01 | Reproducible engineering and deployment foundation | P00 core decisions | 3–5 weeks | Platform/SRE |
| P02 | Trusted identity, tenancy and governance | P01, approved identity contracts | 3–5 weeks | Product engineering + IAM |
| P03 | Application catalogue and operator workspace | P01, P02 tenant/auth interfaces | 3–5 weeks | Product engineering |
| P04 | Site onboarding and read-only inventory | P01, P02 trust interfaces | 4–6 weeks | Infrastructure engineering |
| P05 | Capability assessment and immutable plans | P03 + P04 + policy baseline | 4–6 weeks | Infrastructure engineering |
| P06 | Durable end-to-end operation in simulation | P02 + P05; P01 operational controls | 4–6 weeks | Infrastructure engineering |
| P07 | First native provisioning and safe retirement | P06 gate; commissioned lab and baseline controls | 5–8 weeks | Infrastructure + platform owners |
| P08 | First native application migration and recovery | P07; selected source/method readiness | 6–10 weeks | Infrastructure + application owner |
| P09 | Platform, guest, method and adoption expansion | Reusable P05–P08 contracts; per-tuple prerequisites | 8–16 weeks per planned tranche | Infrastructure + qualification |
| P10 | Enterprise resilience, security and operational acceptance | P08 and every P09 tuple selected for release | 4–6 weeks final campaign | Platform/SRE + security |
| P11 | Commissioned pilot and supported release | P10 gate | 4–8 weeks | Product + service owner |

P02/P03/P04 can overlap once their contracts stabilize. P09 research and adapter development can overlap P07/P08, but qualification cannot skip their safety gates. P10 engineering starts in P01 and runs throughout; its final campaign is repeated after material changes. A narrow first release may defer P09 tuples explicitly. A release claiming all three platforms cannot defer their qualification.

The principal path is P00 → P01 → P02/P03/P04 → P05 → P06 → P07 → P08 → P10 → P11. With concurrent product, infrastructure and platform teams, budget roughly 9–15 months for a narrow first supported release as an initial planning range; re-estimate at P00 and after P06. Broad platform parity is a separate scope and may take longer. A smaller team should reduce concurrency and feature breadth rather than weaken gates.

### P00 — Establish the product and architecture baseline

**Purpose:** remove ambiguity before framework scaffolding fixes accidental design decisions.

| Work package | Deliverable and owner |
| --- | --- |
| P00.01 Scope and journeys | Product: personas, tenant/application/site terminology, supported initial application path, lifecycle journeys and explicit release exclusions |
| P00.02 Domain and ownership | Architecture: context map, aggregate invariants, authoritative writers, resource ownership and temporal state model |
| P00.03 Technical decisions | Engineering/SRE: framework dependency spike, runtime pins, event broker, identity, secrets/PKI, storage, installation target and restricted-network strategy |
| P00.04 Qualification design | Quality/platform owners: selected platform versions, guest image, security topology, migration method, data consistency checks and feasibility report |
| P00.05 Operating requirements | SRE/security: threat model, trust/data flows, provisional SLO/RPO/RTO, scale model, retention, support responsibilities and risk register |
| P00.06 Delivery decomposition | Leads: assign owners, refine estimates, seed contract work, link all R-series requirements to phase packages and identify access/dependency blockers |

The compatibility spike must resolve Composer/npm/Python locks, build the requested Vue/Inertia application, run PHP/TypeScript checks and confirm container support. It should prove the selected stack rather than implement product features. Confirm the selected cold migration method can handle the source disks, boot mode, drivers, network identities and stateful application requirements. If it cannot, record a changed baseline before implementation proceeds.

**Exit gate:** accountable owners accept the product glossary, initial route, contract ownership and decision register; unresolved items have owners and blocking phases; feasibility and dependency resolution have actual results. Repository publication of this plan alone does not close P00.

### P01 — Build the delivery and runtime foundation

**Purpose:** make every service independently buildable, deployable, observable and recoverable from the start.

| Work package | Deliverable and owner |
| --- | --- |
| P01.01 Repository scaffolding | Engineering: `apps/console`, six domain services, worker packages, contracts, automation, deploy and tests; each deployable has owned dependency locks and a build manifest |
| P01.02 Local and integration runtime | SRE: Compose development environment and isolated Kubernetes integration environment with synthetic fixtures and no production endpoints |
| P01.03 Contracts and messaging | Architecture: OpenAPI/AsyncAPI/schema conventions, generated client pipeline, event envelope, transactional outbox/inbox template and broker configuration |
| P01.04 CI and supply chain | SRE: per-service build/test/lint, compatibility checks, secret/dependency/container scanning, SBOM, signed images, immutable digests and release manifests |
| P01.05 Runtime dependencies | SRE: PostgreSQL databases/roles, object storage, Temporal, broker, session/cache store if selected, secrets/PKI and telemetry collector |
| P01.06 Baseline operations | SRE/security: workload identity, deny-by-default connectivity, readiness/liveness, structured logs, backup/restore smoke test, deploy/rollback runbooks and cost baseline |

Use local fakes only for development. Tests requiring database semantics must use the selected PostgreSQL major version. Each service can share a physical cluster initially but has separate ownership, migrations and credentials. Runtime accounts cannot perform arbitrary schema administration or read other contexts' tables. The deployment pipeline runs database changes through a controlled migrator identity.

**Exit gate:** a clean checkout resolves locked dependencies, builds seven application images plus the selected worker image, runs contract checks, installs into an empty integration environment, exercises health/authentication and restores a synthetic database and evidence object. No site administrator credentials are necessary for this gate. Services can roll independently without a full-repository rebuild.

### P02 — Implement identity, tenancy and governance

**Purpose:** establish trustworthy actor, tenant, scope and approval decisions before resource operations exist.

| Work package | Deliverable and owner |
| --- | --- |
| P02.01 Authentication | Product/IAM: OIDC federation, secure browser sessions, CSRF/session expiry, logout, service workload identities, issuer/audience validation and certificate rotation |
| P02.02 Tenancy | Governance: tenants, memberships, delegated grants, scoped roles, environment/site restrictions, quotas and immutable audit events |
| P02.03 Authorization | Governance/security: deny-by-default policy, tenant membership resolution, actor delegation, approval separation of duties and privileged support access rules |
| P02.04 Approval lifecycle | Governance: approvals bound to plan digest/action/scope/expiry, revocation, expiry, change windows and break-glass approval/evidence process |
| P02.05 Console foundation | Console: navigation, tenant selection, access-denied flows, account/session pages and accessible reusable components |

Tenant identifiers in a browser header or URL are selectors, never credentials. Every owning API validates the actor and requested tenant independently of the console. Test direct API access, guessed object IDs, search, exports, event subscriptions, logs and evidence URLs. If database row-level security is chosen, prove runtime roles cannot bypass it; it supplements application authorization.

**Exit gate:** the negative permission matrix passes across at least two tenants and multiple roles. Forged tenant identity, expired/wrong-audience tokens and cross-tenant identifiers are rejected. Revocation prevents new privileged admission; identity failure follows a defined fail-closed behavior. Approval and audit records survive restart and cannot be silently edited.

### P03 — Build the application catalogue and operator workspace

**Purpose:** deliver a useful product model independent of any platform-specific resource schema.

| Work package | Deliverable and owner |
| --- | --- |
| P03.01 Core aggregates | Catalogue: applications, workloads, environments, logical security domains, WSD associations and revisioned desired intent |
| P03.02 Intent semantics | Catalogue: dependency graph, compute/storage/network/service/recovery requirements, workload grouping, lifecycle ownership and schema validation |
| P03.03 Revision behavior | Catalogue: immutable revisions, optimistic concurrency, tenant-scoped idempotency, audit history and outbox atomicity |
| P03.04 Product workflows | Console/catalogue: application create/edit/import, dependency and requirement views, revision comparison, validation errors and status links |
| P03.05 Domain verification | Quality: invalid associations, reference integrity, deleted/revoked membership, concurrent edits, interrupted requests and event replay scenarios |

Keep applications, tenants, WSDs and logical security zones distinct. An application can span WSDs; associations must express the intended ownership and isolation. A platform VM identifier is a discovered resource reference, not the stable identity of the workload. Required unsupported capabilities remain representable and result in assessment failures later; they must not disappear from the model.

**Exit gate:** users can create and revise a multi-workload application, express its security/service intent, view history and receive deterministic conflict errors. Duplicate requests do not create duplicate revisions. Failure to persist the associated outbox record rolls back the mutation. The console uses service APIs without direct domain database access.

### P04 — Commission sites and discover inventory

**Purpose:** obtain trustworthy observations and a controlled site connection before permitting writes.

| Work package | Deliverable and owner |
| --- | --- |
| P04.01 Site enrollment | Inventory/SRE: site and endpoint registration, owner approval, worker enrollment/revocation, allowed endpoints and trust bootstrap |
| P04.02 Collectors | Inventory: read-only OpenStack collector first, VMware source collector next, Nutanix contract and coverage backlog; normalization with stable native identities |
| P04.03 Observation store | Inventory: snapshots/deltas, completeness, timestamp/expiry, provenance, deletion/tombstone semantics and refresh scheduling |
| P04.04 Discovery controls | Infrastructure: per-tenant budgets, pagination, API rate limits, retries, fairness, backpressure and bounded endpoint access |
| P04.05 Inventory experience | Console: site health, platform/version/capability observations, stale/partial warnings and application-resource matching proposals |

Registration is not write commissioning. Endpoint allowlists must prevent discovery from becoming an arbitrary network probe. Credentials stay in the approved secret service; inventory stores references and scope. Observed capacity is not reserved capacity. An unresolved identity collision or missing observation prevents a planner from assuming the resource is safe to use.

**Exit gate:** actual read-only discovery succeeds against the selected OpenStack and VMware lab endpoints. Stable identity survives rediscovery. Partial failures remain visible and expire correctly. Cross-tenant observations do not leak, quotas work and a disconnected site cannot claim fresh readiness. No native resource is changed by this phase.

### P05 — Implement capabilities, policy, placement and immutable plans

**Purpose:** turn portable application intent into an explainable, reviewable technical plan.

| Work package | Deliverable and owner |
| --- | --- |
| P05.01 Capability registry | Planning: versioned operation/constraint vocabulary covering every platform dimension; adapter declarations distinct from qualified support |
| P05.02 Policy and assessment | Planning: requirement/profile resolution, WSD/security placement, service dependencies, sovereignty/location constraints and actionable blockers/remediation |
| P05.03 Capacity and reservations | Planning/lifecycle: reservation intent/contracts, lifecycle-owned reservation journal design, expiry/release semantics and simulated competing-plan behavior; native reservations begin in P07 |
| P05.04 Plan compilation | Planning: canonical immutable plan, digest, operation graph, pinned source versions, inventory references, credential-scope references, expiry and recovery boundaries |
| P05.05 Review experience | Console: destination comparison, unmet/conditional requirements, plan changes, destructive steps, downtime estimate and approval handoff |
| P05.06 Admission contract | Planning/governance/lifecycle: exact approval binding, policy/observation freshness checks, reservation validation and invalidation rules |

Assessment outcomes distinguish eligible, conditionally eligible, unsupported and unknown. Unknown or stale safety facts cannot produce an executable plan. The plan binds intent revision, policy/profile/catalogue versions, adapter/automation artifacts and observed prerequisites. Secrets never enter a plan. A meaningful change creates a new digest and requires new approval. Determinism means equivalent canonical outputs for identical pinned inputs, with variable request metadata explicitly excluded or separately bound.

**Exit gate:** the planner explains eligibility across all three platform profiles, rejects unsupported combinations and produces a deterministic plan for the selected initial path. Deliberate changes to policy, scope, capacity or inventory invalidate admission. Contract tests and simulated reservation races prove the intended no-oversubscription semantics. Planning does not acquire native allocations; actual reservation behavior is qualified in P07. A plan alone grants no write authority.

### P06 — Implement durable execution and evidence in simulation

**Purpose:** prove the entire control path and failure behavior before introducing native mutations.

| Work package | Deliverable and owner |
| --- | --- |
| P06.01 Admission and dispatch | Lifecycle: durable admission record, exact approval recheck, separate lab-campaign versus operational qualification policy, outbox-to-Temporal start, stable workflow ID, idempotency and conflict handling |
| P06.02 Workflow state | Lifecycle: provision/migrate/recover/retire state definitions, activity contracts, timeouts, bounded retries, safe pause/cancel and operator reconciliation |
| P06.03 Execution authority | Lifecycle/workers: short-lived scoped grants, operation journal, resource ownership locks/fencing, native idempotency keys and pre/postcondition contracts |
| P06.04 Evidence custody | Assurance: artifact upload/finalization, hashes, immutable metadata, retention/access policy, operation/plan bindings and qualification decisions |
| P06.05 Simulation and fault injection | Quality: simulated platforms/services, unknown outcomes, duplicate messages, revocation, crashes, lost acknowledgements and prolonged disconnection |
| P06.06 Jobs experience | Console: progress, pending/held/unknown outcomes, cancellation requests, authorized recovery actions and evidence drill-down |

Temporal owns durable workflow progress. Lifecycle's database owns admission, execution authority and the native operation journal; user-facing job status is a projection, not a competing orchestration engine. A lost response must trigger bounded observation/reconciliation, not automatic replay of a possibly completed mutation. Lease expiry cannot prove an old native call stopped. Resource holds persist until safe ownership and outcome are established.

Define a lab-only campaign authorization lane so new adapters can acquire qualification evidence. It must restrict endpoints, credentials, datasets, operations and impact, and retain the same plan, tenant, approval, fencing and recovery safeguards. An independent assurance decision promotes successful evidence to qualified support. Operational admission always requires the relevant qualified tuple; campaign authority never grants production authority.

**Exit gate:** one complete simulated application journey runs through catalogue, planning, governance, lifecycle, workers and assurance. Fault injection proves duplicate admission creates one logical workflow; process restarts resume safely; revoked approvals block later privileged boundaries; retries do not duplicate native effects; and unknown outcomes remain held. The evidence store independently verifies artifact digests. All UI claims clearly identify simulation.

### P07 — Deliver the first native provisioning slice

**Purpose:** provision and retire a real application with the same contracts and controls tested in P06.

| Work package | Deliverable and owner |
| --- | --- |
| P07.01 Native site readiness | SRE/platform owners: write commissioning, scoped credentials, network/storage baselines, backup readiness, quota limits and emergency stop/revocation rehearsal |
| P07.02 Infrastructure automation | Infrastructure: selected OpenStack compute/storage/network adapters and reviewed Terraform plan/apply/state ownership |
| P07.03 Guest and service integration | Infrastructure/service owners: admitted native capacity/IP reservations, approved image, Ansible hardening, identity, DNS/IPAM, time, monitoring/logging and backup enrollment |
| P07.04 Activation and verification | Lifecycle/quality: controlled quarantine-to-active transition, native readback, allowed/denied traffic, same-host/same-subnet checks and application health |
| P07.05 Failure and retirement | Lifecycle: partial-provision recovery, drift holds, safe cleanup, dependencies, retention and deletion confirmation |
| P07.06 Native support dossier | Assurance: exact tuple, qualification evidence, limitations, operator runbook and measured recovery timings |

The first native write requires P01 baseline operational controls and P06 gate closure. Terraform owns its declared fields and state; direct API and Ansible adapters must not compete for those fields. A human-readable dry run is insufficient: execute only the reviewed saved plan and pinned inputs with verified backend/workspace binding. Prove service integration results with their authoritative systems.

Lifecycle owns reservation intent, attempts and receipts; the external capacity/IPAM owner controls the actual allocation. Commit the local journal atomically, perform idempotent owner operations and reconcile or compensate partial outcomes. There is no distributed transaction across these systems. Native reservation acquisition is itself an approved scoped effect, followed by prerequisite validation before dependent mutations.

**Exit gate:** the selected application provisions into a fresh eligible environment, obtains only intended connectivity, is hardened/monitored/protected and is independently observed healthy. Restart and partial-failure campaigns leave reconcilable state. A backup restore verifies recoverability. Retirement releases owned resources and service allocations without touching unowned resources. Qualification is limited to the installed tuple and tested operations.

### P08 — Deliver the first application migration and recovery path

**Purpose:** move a selected real application from VMware to OpenStack with explicit data consistency and authority transitions.

| Work package | Deliverable and owner |
| --- | --- |
| P08.01 Source readiness | Inventory/lifecycle: VMware discovery, application membership/dependencies, boot/storage/network compatibility, source authority and export/capture access |
| P08.02 Method and data movement | Infrastructure: selected offline transfer/conversion or rebuild/restore path, checksums, encryption, resumability, capacity and direct approved endpoint flow |
| P08.03 Rehearsal | Lifecycle/application owner: isolated rehearsal target, representative dataset, measured downtime, application validation and cleanup |
| P08.04 Cutover | Lifecycle/governance: final approval, change window, data quiesce, source fencing, final transfer, target verification and controlled DNS/traffic switch |
| P08.05 Recovery decisions | Infrastructure/application owner: pre-activation rollback, post-write recovery strategy, point of no return, split-brain prevention and explicit human decision states |
| P08.06 Acceptance | Quality/assurance: end-to-end native dossier, data correctness, security equivalence, restore test, interruption matrix and source retirement criteria |

Represent whole-VM cold conversion/import and application rebuild/restore as separate migration methods. A successful rebuild does not qualify preservation of VM identity, disks or guest configuration. The selected method must be recorded in the plan and support matrix. Data moves between approved site endpoints; the console, general event bus and central databases do not transport workload payloads.

Before enabling target writes, establish source fencing and the selected rollback boundary. After target writes, do not advertise a safe source rollback without a demonstrated data reconciliation procedure. A timeout during cutover must enter an explicit held/recovery state. Source decommissioning follows verified acceptance and retention requirements, not simply completion of the last activity.

**Exit gate:** rehearsal and real cutover on the selected lab application meet owner-approved integrity and outage objectives; source/target authority is unambiguous; intended security policies remain effective; injected interruption can be recovered without an unreviewed retry; and restoration is demonstrated. Record exact platform versions, guest profile, migration direction, method, data size and topology. Reverse migration remains unqualified.

### P09 — Expand platforms, capabilities and adoption

**Purpose:** add breadth through contracts and separately proven support tuples.

| Work package | Deliverable and owner |
| --- | --- |
| P09.01 Platform tranches | Infrastructure: VMware and Nutanix provisioning/lifecycle adapters, platform-specific capabilities and service insertion/network/storage variants |
| P09.02 Migration matrix | Infrastructure/quality: additional source/target directions and methods, Windows/Linux profiles, boot modes and application/data classes |
| P09.03 Brownfield adoption | Inventory/lifecycle: ownership claims, duplicate detection, drift review, explicit imports, Terraform state adoption and detach/relinquish behavior |
| P09.04 Enterprise capabilities | Planning/workers: HA/recovery variants, shared services, capacity, scaling, policy changes, patching, certificate rotation and day-two operations |
| P09.05 Extension contract | Architecture: adapter packaging, declared constraints, signed artifact/version identity, conformance kit and compatibility documentation |

Sequence tranches by business demand and feasibility. Full profiles must include unsupported capabilities with explanations; profile completeness is not platform parity. Each new material variation receives its own test evidence. Common service contracts can be reused; native acceptance cannot. Qualified support expires or is invalidated when relevant versions, security rules, automation or environmental assumptions change.

**Exit gate per tranche:** requirements and service contracts are complete, native evidence supports every claimed tuple, affected common-path campaigns are rerun and operations can deploy/upgrade/recover the new adapter. Release scope lists included and deferred tuples explicitly.

### P10 — Complete enterprise reliability and operating qualification

**Purpose:** close production-readiness risks under representative failure, load and upgrade conditions.

| Work package | Deliverable and owner |
| --- | --- |
| P10.01 Resilience and performance | SRE/quality: multi-failure-domain control plane, dependency failover, representative inventory/job load, quotas, API limits, queue recovery and capacity report |
| P10.02 Recovery and upgrades | SRE: coordinated database/Temporal/broker/evidence/secrets recovery, expand/contract migrations, workflow replay/versioning and rolling worker upgrades |
| P10.03 Security assurance | Security: tenant isolation, threat-model findings, dependency/artifact trust, external assessment as required, secrets/certificate/key rotation and access reviews |
| P10.04 Operations | SRE/service owner: on-call, incident runbooks, dashboards/alerts, retention, evidence export, support tiers, cost model and maintenance windows |
| P10.05 Installation qualification | SRE/quality: clean install, restricted-network artifact promotion if required, trust enrollment, rollback/recovery and decommission rehearsals |
| P10.06 Release dossier | Quality/product: all selected native tuples rerun on release candidates, remaining risks, acceptance evidence and sign-off record |

HA and backups are delivered incrementally from P01. This phase tests their complete behavior. Restoring old operation state must not repeat external writes: quarantine resumed jobs, inspect native outcomes and re-establish ownership before admission. Backing up PostgreSQL alone does not restore Temporal histories, evidence, cryptographic keys or Terraform state.

**Exit gate:** agreed SLO/load targets and RPO/RTO are demonstrated; recovery does not create duplicate native writes; supported mixed versions run through upgrades; required security issues are resolved; the service owner accepts support responsibilities; and every support claim matches evidence from the release candidate.

### P11 — Commission a pilot and release

**Purpose:** demonstrate the product as an operated service and publish a bounded, supportable release.

| Work package | Deliverable and owner |
| --- | --- |
| P11.01 Production commissioning | SRE/service owners: environment readiness, access grants, tenant/site onboarding, credentials, backups, monitoring and approved operational windows |
| P11.02 Controlled pilot | Product/operators: first tenant/application, user training, rehearsal, bounded native execution and agreed observation period |
| P11.03 Acceptance | Application/security/service owners: functional outcomes, isolation, performance, recovery, audit evidence and support handover |
| P11.04 Release publication | Engineering/SRE: signed release manifest, images/locks/SBOM, install/upgrade guides, supported tuples, limitations and support contact ownership |
| P11.05 Historical disposition | Product/records owner: no-data migration declaration or explicit archive/import plan for retained intent/evidence; verification before any old system retirement |

**Exit gate:** the pilot meets documented acceptance criteria, an operator other than the developer can install and recover the release using its runbooks, and the release manifest reconciles code/configuration, evidence and support claims. No old branch or operational data is deleted as an incidental part of pilot closure.

## 4. Greenfield deployment sequence

Use a central control plane per approved trust/residency boundary and scoped site-local workers. Separate tenant network/security isolation from container scheduling; a Kubernetes namespace alone is not a tenant security design. Do not assume one control plane may span every security classification or disconnected enclave.

| Stage | Deployment action | Required evidence |
| --- | --- | --- |
| D01 Infrastructure prerequisites | Select sites/failure domains; establish DNS, time, PKI, registry, storage, secrets and approved ingress/egress | Ownership, network reachability and recovery prerequisites |
| D02 Stateful dependencies | Deploy supported PostgreSQL, Temporal persistence/server, broker and protected object storage | Version pins, least privilege, backup restore and health |
| D03 Domain services | Run controlled migrations; deploy governance/catalogue/inventory/planning/lifecycle/assurance and console | Per-service health, authentication and compatible contracts |
| D04 Observability | Connect telemetry, dashboards, audit sink, alert routing and synthetic journeys | Correlated request-to-operation trace with secret redaction |
| D05 Site trust | Enroll workers, bind task queues/endpoints/scopes, install approved artifacts and secret references | Read-only handshake, revocation and partition behavior |
| D06 Safe initial data | Bootstrap minimum administrator through controlled process; install reviewed profiles/policies; onboard first tenant | No baked-in credentials; approval and isolation checks |
| D07 Read-only acceptance | Discover actual target/source, validate freshness, produce a plan and inspect evidence | No native writes; operator acceptance of readiness |
| D08 Native enablement | Grant the exact tested operations within the change window and admitted plan | P06/P07 controls, emergency stop and recoverability |
| D09 Pilot activation | Execute approved pilot, verify service and observe against SLO | Application/security/service-owner acceptance |

Build once and promote identical signed image digests through developer, integration, native qualification, preproduction and production environments. Keep environment configuration and secrets outside images. Pin Helm/Kubernetes and infrastructure dependency versions in P00/P01. GitOps is a proposed deployment mechanism, subject to the selected enterprise platform; it does not grant native workload execution authority.

For restricted sites, mirror the full dependency closure, images, charts, guest artifacts and signatures; verify installation with public internet blocked. Offline site execution is not assumed: specify authority expiry and permitted continuation at safe boundaries. Reconnection reconciles observations and journals before new writes.

## 5. Cross-cutting quality and operating targets

These numbers are **proposed sizing and acceptance inputs**, not promises or inherited organizational requirements. P00 must replace or ratify them with a workload model and owners; qualify the agreed values in P10.

| Area | Starting target or decision input | Measurement |
| --- | --- | --- |
| Control-plane availability | 99.9% monthly for authenticated core API journeys, excluding agreed maintenance | Synthetic user journeys and dependency-aware service indicators |
| Interactive latency | p95 ≤ 2 seconds for catalogue/plan-review reads under agreed test load | Server + browser trace; large assessments remain asynchronous |
| Command acceptance | p95 ≤ 3 seconds to validate and durably admit an eligible command | Does not include native execution duration |
| Recovery | Control-plane RPO ≤ 15 minutes and RTO ≤ 4 hours as design candidates | Measured full restore; native unknown outcomes must still be held |
| Data and migration | Application-specific RPO/RTO/downtime and correctness targets | Selected workload/owner acceptance, separate from control-plane targets |
| Scale | Parameterized tenant/site/resource/discovery/job model | P00 selects initial and growth tiers; include API quotas and data transfer bandwidth |
| Isolation | Zero successful unauthorized cross-tenant operations in defined campaigns | Negative API, event, storage, export and recovery tests |
| Accessibility | Keyboard/screen-reader operability, visible focus, readable error/state feedback | Automated checks plus manual critical-journey review; exact required standard selected in P00 |
| Retention | Owner-defined evidence/audit retention, residency, export and erasure rules | Policy enforcement and restoration/deletion tests |

Testing layers are: domain invariants; API/event/schema compatibility; real dependency integration; end-to-end browser journeys; simulator fault campaigns; native platform/service campaigns; operational load/restore/upgrade campaigns; and pilot acceptance. Each layer answers a different question. Keep synthetic fixtures permanently identified as synthetic.

Prevent noisy-neighbor effects through tenant quotas, fair scheduling, bounded discovery and worker concurrency, native API rate limits and data-mover bandwidth controls. Do not infer resource reservations from cached inventory. Maintain usage/capacity reporting and evaluate showback in P09 without making a billing platform a first-release dependency.

## 6. Risks, decisions and delivery control

| Risk | Mitigation and blocking point |
| --- | --- |
| Service count creates excessive operational work | Seven principal deployables; contracts and owners first; shared platform tooling; no per-capability service explosion (P00/P01) |
| Framework compatibility differs from requested majors | P00 lock/build/container spike and supported patch/runtime selection |
| Platform API or conversion limitations invalidate migration | P00 feasibility and P04 observations; exact method qualification in P08 |
| Business rules drift between PHP and Python | One authoritative owner, generated contracts, cross-language conformance cases (P03/P05) |
| Duplicate or uncertain external side effects | Durable operation journal, scoped authority, fencing and reconciliation before retry (P06) |
| Lab/integration-owner access arrives late | Named dependency owners and access dates in P00; do not replace native gates with simulator claims |
| Control-plane recovery replays unsafe writes | Restore in held mode; reconcile native resources and state before resuming (P10) |
| Scope claims exceed demonstrated support | Per-tuple evidence and explicit unsupported matrix (P07–P11) |
| Greenfield development loses earlier domain requirements | R-series traceability and historical reference register without old runtime inheritance |

At each phase review, update [progress](progress.md), [requirements coverage](requirements-and-qualification.md), the [decision register](../decisions/decision-register.md) and [next work](../../next_work.md). Record evidence identifiers, exact versions, open risks and accountable acceptance. A failed gate creates a concrete corrective work package; it does not silently move the gate later.

For a future implementation request, start with P00 work in `next_work.md`, then implement small complete vertical slices through the owned services. Do not claim the entire programme complete from a single generated scaffold, a passing unit suite or an unexecuted deployment manifest.
