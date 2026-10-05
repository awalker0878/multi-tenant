# Enterprise requirements and qualification

**Status:** Proposed delivery baseline; all new implementation and qualification evidence starts empty. **Date:** 2026-10-04.

This register translates enterprise hosting and workload-mobility requirements into the new P00–P11 programme. Historical implementation is reference material only: no old completion flag, passing test, credential, approval, native support claim or operational acceptance transfers into this product. The abandoned Laravel foundation branch is not a dependency.

## 1. Traceability and completion rules

Every implementation issue names its requirement IDs, accountable context, work package, contract or ADR, acceptance criterion, source revision and unresolved dependency. The [status model](status-model.md) defines independent work, verification, native qualification and operational acceptance axes. The [delivery register](delivery-register.yaml) owns their values and evidence references; [traceability](traceability.md) connects requirements to packages, decisions, contracts, campaigns and gates. This document owns requirement wording, domain constraints and campaign intent. Completing repository work cannot satisfy a missing native or operating gate.

Priority `M` means mandatory for the indicated milestone; `E` means mandatory before the advertised expansion; `O` means optional until a selected service requirement makes it mandatory. Phase mapping establishes first delivery and later breadth, not permission to postpone safety controls until P10. Minimum observability, recovery and credential controls must operate before P07 native writes.

| ID | Priority | Requirement and verifiable outcome | Delivery phases | Accountable context |
|---|---|---|---|---|
| R01 | M | Fresh product baseline, bounded contexts, canonical vocabulary, ownership map, acceptance scope and chosen migration method approved as design decisions; no runtime dependency on legacy code. | P00–P01 | Architecture / delivery |
| R02 | M | Independently built services, dependency locks, versioned HTTP/events, contract compatibility, deployment manifests, provenance and isolated credentials; no service reads another service's private tables. | P01, P10 | Delivery / all owners |
| R03 | M | Console-managed external OIDC; deployment-created local administrator with random displayed password, mandatory first-login change and retirement at verified federation; tenant membership, delegated roles, resource/action scopes, separation of duties, approval revision binding, revocation and attributable break-glass access. | P02, P06 | Governance |
| R04 | M | Tenant isolation across APIs, database access, object storage, projections, events, search, job status and evidence; negative tests cover guessed IDs and confused service callers. | P02–P06, P10 | Governance / all owners |
| R05 | M | Revisioned applications, workloads, datasets, dependencies, service owners and acceptance criteria; concurrent edits reject stale revisions and retries cannot create duplicate intent. | P03 | Catalogue |
| R06 | M | Tenant, WSD, logical Security Domain and native Domain Instance stay distinct; support multi-workload/multi-domain applications and explicit domain sharing decisions. | P00, P03, P05 | Catalogue / planning |
| R07 | M | Tenant VPC/network-domain intent realizes independent routing and policy scope, address-family requirements, mandatory tenant/WSD isolation and controlled inter-domain boundaries. | P03, P05, P07, P09 | Planning / execution |
| R08 | M | Site commissioning records accepted transport, compute, storage, management, edge/attachment capacity, failure domains, service dependencies, ownership and exact installed tuples. Uncommissioned capacity is ineligible. | P04–P05, P07, P09 | Inventory / assurance |
| R09 | M | VMware, Nutanix AHV and OpenStack read profiles define complete fact contracts, native identities, paging, privilege coverage and provenance; missing facts remain unknown. | P04, P09 | Inventory |
| R10 | M | Discovery campaigns use scoped read authority, enrolled collectors, credential provenance, bounded endpoint budgets, resumable generations, freshness and independent coverage reconciliation. | P04 | Inventory |
| R11 | M / E | Mandatory early safeguards keep discovered unowned resources observation-only and reject ownership collisions. Advertised brownfield adoption additionally proves exact object/field scope, no-change import/reconciliation and separate transfer approval before mutation in P09. | P04–P05 safeguards; P09 adoption | Inventory / lifecycle |
| R12 | M | Explainable destination comparisons pin inventory generations, intent, policy and qualification; reject stale evidence and show eligible, blocked and unknown outcomes with remediation. | P05 | Planning |
| R13 | M | Versioned platform profiles span all capability dimensions below; mandatory requirements for operational admission need current exact-tuple evidence and cannot be silently downgraded or inferred from a vendor name. New qualification uses separately authorized, isolated lab campaigns. | P04–P06, P09 | Planning / assurance |
| R14 | M | Immutable reviewed plans bind exact objects, mappings, dependencies, budgets, effect sequence, recovery boundaries, qualification and approval; any material change invalidates approval. | P05–P06 | Planning / governance |
| R15 | M | Durable workflow admission, transactional outbox, idempotent consumers, replay-safe orchestration, cancellation and independent effect reconciliation survive process and network failures. | P06 | Lifecycle |
| R16 | M | One writer per owned resource/field scope; worker identity, leases/epochs, revocation and qualifications rechecked immediately before effects; unknown completion holds further mutation. | P06–P07 | Lifecycle / execution |
| R17 | M | Capacity, IPAM, snapshot, staging, target and retained-source budgets use a lifecycle-owned atomic local journal and idempotent reserve/renew/confirm/release operations at each authoritative owner, with reconciliation/compensation for partial outcomes. Expiry cannot release observed live resources. P05 tests contracts/simulation; native effects begin P07. | P05–P07, P08 | Lifecycle / adapters |
| R18 | M | OpenStack provisioning completes prepare, saved plan, approval, apply, independent observation, readiness, guest configuration, service checks and controlled activation through the console. | P07 | Lifecycle / execution |
| R19 | M | Explicit multi-VM/disk/NIC ordering, boot/firmware, address, storage and failure-domain mappings; selected Linux guest/image hardening and readiness are qualified, with unsupported features rejected before writes. | P03, P05, P07 | Catalogue / execution |
| R20 | M | Portable policy covers required flows and deny rules; native realization proves equivalent outcomes, protected selectors, mandatory precedence and no same-host, same-subnet or transit bypass. | P05, P07–P09 | Planning / assurance |
| R21 | M | DNS, IPAM, identity, time, trust, logging, monitoring and backup integrate through named owner contracts and receipts; activation requires usable service, reply paths and verified restore. | P05, P07–P08 | Lifecycle / adapters |
| R22 | M | First VMware→OpenStack offline route covers every approved dataset, consistency group, source/target scope, integrity/metadata, secrets/keys and bounded transfer/staging demand. | P06, P08 | Lifecycle / data workers |
| R23 | M | Rehearsal suppresses production writers and business side effects; cutover requires independently observed source/other-writer fencing, final sync, accepted data and controlled traffic activation. | P06, P08 | Lifecycle / execution |
| R24 | M | Pre-target-write rollback and post-target-write recovery are separate procedures; accepted target changes cannot be discarded by restarting the old source. Prove source-return or approved forward recovery. | P06, P08 | Lifecycle / application owner |
| R25 | M | Retirement has separate authority for source deletion, identity/address release and data disposal; retain required data and keys, verify cleanup and record sanitization evidence. | P07–P08, P10 | Lifecycle / governance |
| R26 | E | Independently qualify six directed cross-platform routes across VMware, AHV and OpenStack; same-family relocation is topology-specific. Method, guest and recovery evidence is never inferred in reverse. | P09 | Platform teams / assurance |
| R27 | E | Windows, appliance/no-guest-mutation, whole-VM conversion and selected database synchronization profiles have explicit scope, constraints, drivers, encryption and recovery evidence. | P09 | Platform / guest / data teams |
| R28 | E | Enterprise wave scheduling obeys dependency DAGs, windows, tenant fairness, shared endpoint/risk budgets, pause/stop semantics and bounded concurrent impact. | P09–P10 | Lifecycle |
| R29 | M | Control-plane and worker recovery covers DB, workflows, evidence, state, identities and keys; isolated restore starts read-only and reconciles epochs/accepted intent before enabling writes. | P01, P06–P07, P10 | Platform operations |
| R30 | M | Correlated logs/traces/metrics, freshness/drift/stuck-job alerts, actual alert delivery, acknowledgements, ITSM/CMDB handoffs, incident containment and support runbooks are exercised. | P01, P06–P07, P10 | Operations / all owners |
| R31 | M | Signed artifacts and evidence, redaction, encryption/key custody, least privilege, conversion/data-worker isolation and independent security review meet the selected assurance profile. | P01–P02, P06–P10 | Security / assurance |
| R32 | M | Sovereignty requirements identify permitted hosting/backup locations, administrative jurisdiction/access, support access, keys and evidence custody; enforcement is evaluated against actual deployment. | P00, P02, P05, P10 | Governance / security |
| R33 | M | UI supports complete operator tasks, clear holds and authorized recovery actions; keyboard/accessibility, stale state, safe retries and delegated role usability tested with representative users. | P03–P08, P11 | Console / product owner |
| R34 | M | Agreed scale/SLO/outage/data targets have reproducible measurement plans; P00 selects initial and growth tiers by tenant/site/resource counts, discovery rates, job concurrency and transfer bandwidth. No estate scale is treated as a passed capacity claim. | P00, P04, P10 | Product / performance |
| R35 | M | Upgrade, downgrade constraints, API/event compatibility, workflow version routing, retention, signed release and supported capability matrix bind final artifacts; pilot and receiving-team acceptance precede GA. | P01, P10–P11 | Delivery / operations |
| R36 | O | If retained operational state exists, one-time import preserves originals and reconciles counts/digests/native IDs under observation-only access, then freezes old writers. Otherwise record reviewed non-applicability. | P00, P10 | Product / lifecycle |

## 2. Domain invariants

A **Tenant** is an administrative allocation with membership, entitlements and quotas. A **Workload Security Domain (WSD)** groups resources by service owner, lifecycle and security/recovery requirements; it is not an application microservice or necessarily one Terraform state. A **logical Security Domain** names zone class and security authority; a **Domain Instance** realizes that domain in an actual site/platform routing and enforcement context. One network belongs to one domain instance. Independent tenants retain independent contexts even where both use the same OZ or RZ label.

The model must support PAZ, OZ, RZ and HRZ requirements, with management scope explicit. A **Zone Interface Point (ZIP)** is a controlled interface between zones, not a workload zone. Required inspection, stateful policy, logging and forward/reply paths must exist in the qualified realization. A router, firewall licence or diagram alone proves none of these outcomes. Shared security/edge hardware is possible only where logical isolation, administration, finite capacity and correlated-failure implications are accepted.

Keep requested intent, observed inventory, assessed eligibility, approved plans and actual native state separate. Native platforms and service owners remain authoritative for real resources. Observations do not grant ownership, capability qualification does not grant authorization, and approval of one immutable plan does not authorize a changed plan or retirement.

## 3. Complete profile dimensions for all three platforms

Every VMware, AHV and OpenStack profile must contain every dimension below, including explicit `UNASSESSED`, `UNSUPPORTED` or conditionally supported entries. Completeness means no hidden dimension; it does not mean every platform must implement every optional feature. Required unsupported outcomes block placement. Define requirement semantics first and evaluate each realization; never rank whole vendor families from partial feature lists.

| Dimension | Required profile coverage and qualification focus |
|---|---|
| Installed identity | Product/service/API versions, API microversions where relevant, backend/plugins, adapters/providers, enabled features and entitlements, site and deployment configuration. |
| Compute and placement | CPU architecture/features, memory, quotas, affinity/anti-affinity, failure domains, evacuation/HA, maintenance, resize and power lifecycle; GPU/passthrough recorded explicitly. |
| Storage and datasets | Block/file/object consumption, datastore/volume placement, replication, snapshots, consistency groups, shared/multi-attach disks, encryption, keys, I/O limits and observed cleanup. |
| Network and tenant VPC | Isolated domains, subnet and gateway mapping, IPv4/IPv6, overlapping address scopes, routing/NAT, MTU, attachments, floating/public exposure and path symmetry. |
| Security and edge | Distributed east–west enforcement, gateway policy, mandatory-rule precedence, protected identity selectors, ZIP functions, service insertion, load balancing, dedicated edge contexts and audit. |
| Guest and image | Linux/Windows/appliance profiles, image provenance, BIOS/UEFI, secure boot/vTPM, drivers, cloud-init/Sysprep equivalents, hardening, guest identity and readiness boundaries. |
| Lifecycle and adoption | Discover, compare, create, observe, adopt, update, replace, resize, power, recover and delete; ownership scope, idempotency, no-change import and uncertain-operation readback. |
| Mobility | Each source→target direction, export/import/conversion or application restore method, disk chains, network remapping, downtime, data consistency, writer fencing and post-write recovery. |
| Shared services | Scoped DNS/IPAM, directory/identity, NTP, PKI, secrets, backup/restore, logging, monitoring, ITSM/CMDB and their initiation/reply and management paths. |
| Resilience and operations | Control/data-plane failure behavior, surviving eligible capacity, fail-secure paths, degraded mode, rate limits, pagination, upgrade compatibility, observability and recovery dependencies. |
| Assurance and sovereignty | Information/availability impacts, location, administrative and key custody, privilege boundaries, evidence retention, approved exceptions and authorization scope. |

Compare actual operation outcomes, including alternate qualified integrations; do not assume identical topology, identical provider coverage or that one Terraform provider provisions an entire platform. Separate virtual disk I/O, guest file/object access, backup transfer, replication and their control planes.

## 4. Qualification tuple and evidence levels

A support claim identifies: **source tuple (if any), target tuple, direction, operation/method, guest/image profile, data/consistency profile, network/policy/service profile, topology/failure model, assurance profile and tested product artifact revisions**. Each installed tuple includes platform/API/backend/feature/entitlement versions and site configuration identity. Attach campaign ID, timestamps, evidence digests, independent observer, scope, limitations, expiry/retest triggers and revocation state. Native endpoints and sensitive material remain in approved operational systems.

| Level | What it demonstrates | What it cannot claim |
|---|---|---|
| E0 — Requirement/design | Explicit requirement, contract, ADR and planned test. | Implemented behavior or platform support. |
| E1 — Unit/contract verified | New code, schema and deterministic rules pass tests at recorded revision. | Deployed interoperability or native effects. |
| E2 — Integrated/simulated | New services, real local persistence and workflow engines exercise contracts, faults and recovery with controlled doubles. | Native platform support, security equivalence or production readiness. |
| E3 — Native qualified | Authorized tests on exact installed tuples independently observe positive, negative, failure and recovery outcomes. | Production change approval or receiving-team acceptance. |
| E4 — Operationally accepted | Deployment, security/operations owners and pilot users accept the tested service scope, support and measured objectives. | Untested tuples, directions, methods or future releases. |

Evidence cannot advance by editing a flag. Assurance validates provenance, scope, freshness and compatibility against requirements; mandatory missing or invalid evidence produces a hold. A changed artifact or relevant tuple/configuration invalidates affected claims until impact analysis and the required rerun complete. Unaffected reuse requires an explicit scope decision, never blanket inheritance. Catalogue completeness, qualified support and permission to execute remain separate views.

## 5. Acceptance campaigns

| Campaign | Minimum useful test set | Requirements / first gate |
|---|---|---|
| Q01 — Contract and tenancy | PHP/Python contract compatibility; tenant/resource denial; forged caller, stale revision, duplicate command and projection isolation; outbox atomicity. | R02–R06, P03/P06 |
| Q02 — Discovery and adoption | All three profile contracts; partial pages, hidden privilege scope, stale/revoked collector, reused IDs, incomplete generations and ownership collision; native no-change import when adoption enters support scope. | R08–R11, P04 discovery; P09 adoption |
| Q03 — Planning and authority | Two authorized destinations; missing/stale qualification, unsupported mandatory controls, invalid plan approval, revoked access, reservation races and stale inventory. | R12–R17, P05/P06 |
| Q04 — Durable execution | Crash before/after native acceptance; lost response; duplicate delivery; lease expiry; approval revocation mid-job; old worker resumes; confirm observed result before retry/release. | R15–R17, R29–R31, P06/P07 |
| Q05 — Native provisioning | Selected OpenStack site, complete guest/service path, multi-NIC/disk mapping, quarantine, failed activation containment, backup restore, managed change and explicit retirement. | R07–R08, R18–R21, R25, P07 |
| Q06 — Policy equivalence | Positive application flows and negative tenant/tier/isolation tests across same-host/subnet/host and edge paths; selector tampering, IPv6, NAT/return and failover/bypass cases. | R06–R08, R20, R31, P07/P09 |
| Q07 — First offline migration | VMware→OpenStack exact selected method; all datasets, quiesce/fence, final sync, integrity, exposure, measured downtime/data objective, target-first-write failure and accepted recovery. | R22–R24, P08 |
| Q08 — Route expansion | Separate campaigns for all six directed platform routes, selected same-family topologies and every advertised Linux/Windows/appliance or transfer method. | R26–R28, P09 |
| Q09 — Deployment and recovery | Clean install, restricted/disconnected delivery if required, rolling upgrade, incompatible contract rejection, DB/workflow/evidence restore, lost site and key/identity dependency recovery. | R02, R29–R32, R35–R36, P10 |
| Q10 — Scale and pilot | Approved estate workload mix, endpoint limits and UI performance; concurrent-wave stop behavior; alert receipt/on-call exercises; role-based operator tasks and accepted production pilot. | R28, R30, R33–R35, P10/P11 |

P00 must select the initial P08 offline method. The preferred proposal is **application rebuild/restore from VMware to a newly provisioned OpenStack target**, contingent on reproducible deployment/configuration and demonstrated consistent capture, restore completeness and cutover recovery for the selected profile. Cold VMware guest/disk capture, conversion and OpenStack import remains a separate P09 candidate for applications that cannot be rebuilt. A change of method needs an explicit scope decision; neither is an automatic fallback. Keep both methods in the catalogue but initially qualify only the selected one; evidence for either never proves the other. Whole-VM claims require disk-chain, boot, device, driver, encryption and imported-guest checks; application restore claims require dataset and reconstruction coverage. Warm/live movement and zero-downtime claims require separate implementation and qualification in P09 or a later release.

## 6. Scope decisions and material risks

| Decision / risk | Required treatment |
|---|---|
| Native access is not yet available | Continue contracts and integration work; record exact owner/input blocking each E3 campaign. No synthetic pass substitutes for native qualification. |
| First useful slice expands indefinitely | Lock one representative Linux application, selected source/target tuples and offline method in P00; retain enterprise dimensions and later obligations explicitly. |
| Site commissioning is confused with registering an endpoint | Require engineering inputs, constrained credentials, accepted edge/service/capacity and actual observations before P07 writes. |
| Framework microservices fragment authority | Keep single domain/data owners, end-to-end traceability and decision-time authority checks; events propagate facts and do not create approvals. |
| Policy/HA claims omit hidden data paths | Test connected routes, same-host forwarding, source identity, inspection failure, return paths and surviving eligible capacity. No weaker policy on failover. |
| Brownfield import inherits unsafe writers | Begin observation-only, enumerate field ownership and old actors; freeze/transfer authority explicitly. Importing inventory does not mean managing it. |
| Recovery overlooks target writes or keys | Approve the divergence strategy and key/backup availability before cutover; rehearse it with actual application data and independent readback. |
| Optional features are hidden in generic platform support | Publish unsupported rows for appliance, GPU, passthrough, shared-disk, vTPM/encrypted and warm/live requirements until separately qualified. |
| Enterprise integrations are assumed from examples | Confirm actual owners, APIs, entitlements and operational contracts. Commvault/Infoblox or vendor-specific storage integrations are scope decisions, not automatically accepted adapters. |

## 7. Historical requirement sources

Source checkout reviewed read-only at `a9c7a2fbb2a97acce2b4ad007b098292673c9fbf` in `awalker0878/multi-tenant`. This pins source provenance only; it asserts no current legacy status and supplies no implementation or qualification evidence to the new product.

- `docs/product/enterprise-workload-mobility-execution-plan.md`: historic B01–B50 capability and execution-safety obligations, directed routes, usable-service and final-release gates.
- `docs/current/RAD-adoption.md`, `TAD-infrastructure.md`, `internal-hosting-solution.md`, `interface-agreements.md`, `transition-and-as-built.md`: adoption, commissioning, boundaries, ownership and recovery obligations.
- `docs/architecture/reference/7-tenant-environments-and-security-domain-placement.md` and `8-zone-interfaces-routing-and-security-edge-topology.md`: tenant/WSD/domain distinctions, ZIP semantics and policy paths.
- `docs/engineering/platform-capability-registry.md` and `sources/capabilities/platform_registry.json`: qualification versus declaration boundary; the new profiles cover the complete dimensions defined in this register.
- User attachment `Pasted markdown(6).md`: greenfield Laravel/PHP business contexts, Python infrastructure/lifecycle services, independent deployment and previous code as reference. Its historical status narrative is not carried into this plan.
