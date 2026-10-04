# Estimates, capacity inputs and delivery dependencies

**Status: planning assumptions, not staffing commitments or measured throughput.** The [phased plan](phased-plan.md) owns phase sequence and duration ranges. This document explains the conditions behind them, how to size the operated product and when to re-estimate. It does not assert current lab access, assigned people or a funded delivery date.

## 1. Conditional delivery scenario

The existing **roughly 9–15 months** is a broad elapsed-calendar estimate for a narrow first supported release, conditional on concurrent product, infrastructure and platform work and timely external access. It is not a sum of all phase ranges. P02/P03/P04 overlap after contract prerequisites; operational engineering runs throughout; the P10 range is a final campaign. P09 tranches are additional scope unless explicitly selected for the first release.

The nominal dependency path is P00 → P01 → P02/P03/P04 → P05 → P06 → P07 → P08 → P10 → P11. Illustrative elapsed working-week ranges on that path total approximately 36–58 weeks when the three early branches overlap, before calendar availability and external wait adjustments. This arithmetic explains the broad range; it is not a resource-loaded schedule, probability forecast or evidence that parallel work has been staffed. Late access, failed feasibility or mandatory expansion can exceed it.

| Workstream | Illustrative sustained allocation | Responsibilities and concurrency assumptions |
| --- | --- | --- |
| Product engineering | 2–3 full-time equivalents | Laravel contexts, console and operator journeys; P02/P03 can share stable contracts but have different owned outputs |
| Infrastructure engineering | 3–4 full-time equivalents | Inventory/planning/lifecycle, workers, adapters and data path; at least enough separation for core workflow and platform integration |
| Platform/SRE | 2 full-time equivalents | Runtime/build system, identity integration, observability, recovery and deployment; continues during feature phases |
| Quality/qualification | 1–2 full-time equivalents | Contract/fault campaigns, native independent observations and evidence review; additional specialist reviewers still required |
| Product ownership | 0.5 full-time equivalent | Scope, representative application, decisions and user acceptance coordination |
| Architecture | 1 full-time equivalent | Domain/contracts, ADRs, cross-context consistency and review; may be staffed across leads if capacity is explicit |
| Security/IAM | 0.5 full-time equivalent | Trust/authorization, credential and assurance design; dependent on enterprise owner availability |

This illustrative core allocation is roughly 10–13.5 full-time equivalents. Platform, network, storage, IPAM/DNS, backup, application/data, IAM and receiving-team owners are additional part-time dependencies; their availability cannot be replaced by developers simulating responses. Do not count the same person simultaneously as a full engineering lead, independent reviewer and external service owner. This scenario is a planning sensitivity case, not a recommended headcount commitment.

With a smaller team, sequence workstreams and reduce the selected release breadth. Preserve native safety and recovery gates. More developers do not remove API access lead time, scarce test environments, serial qualification or independent approval requirements.

## 2. Estimate construction and confidence

| Estimate component | Required basis | Current confidence / action |
| --- | --- | --- |
| Core service implementation | Work-package outputs, agreed contracts, engineering availability and comparable measured delivery | Low before P00/P01; refine after the first complete contract/integration slice |
| Platform adapters / conversion | Exact APIs, entitlements, guest/device formats and completed feasibility spikes | Low before platform access; do not estimate from vendor names alone |
| Native campaigns | Test-case count, setup/reset time, data volume, failure/recovery duration and independent observers | Low until Q05 rehearsal; estimate repetitions and failed-case correction separately |
| Operations and security | Accepted operating targets, hosting platform, control requirements and review capacity | Low until ADR-017/020 and owner responsibilities resolve |
| External waits | Named prerequisite, owner, requested/confirmed dates and escalation path | Unknown until owner acknowledgement; carry as calendar dependencies, not coding effort |
| P09 breadth | Enumerated route × method × guest × topology tuples and reuse impact analysis | Unbounded until tranche selected; do not multiply only three platform families |

For each work package, record effort range by role, elapsed duration, prerequisites, parallelism limits, assumption IDs, confidence, unavailable capacity and next review date. Distinguish engineering effort, unattended transfer/runtime and external waiting. Capture actual elapsed/effort after delivery to recalibrate later phases. Keep contingency visible for named uncertainties instead of hiding it inside every task and adding it again at programme level.

Use optimistic/most-likely/pessimistic scenarios only after their assumptions can be explained; do not invent statistical confidence such as P80 from an uncalibrated range. Final milestone dates require a resource-loaded schedule and confirmed external dates.

## 3. External dependency register to establish in P00

These rows define required inputs and accountable roles, not assigned individuals or confirmed access. Link the resulting live dependency records from affected work packages; the [delivery register](delivery-register.yaml) remains the authority for current blockers/status.

| Dependency | Required input / accountable role | Blocks | Safe work available while unresolved |
| --- | --- | --- | --- |
| DEP-01 Runtime and artifact access | SRE/delivery: approved deployment target, registry/mirrors, package resolution and build/runtime constraints | P00 compatibility spike; P01 foundation | Domain examples, contract drafts and architecture tradeoffs |
| DEP-02 Identity and delegation | IAM/security: test IdP, issuers/audiences, service identities, revocation, claims and delegated action policy | P02 authority and P06 native admission | Synthetic authority conformance cases; no production authority claim |
| DEP-03 VMware source tuple | Platform owner: installed version/API, entitlements, read/export scopes, test resources and capture constraints | P00 feasibility, P04 reads, P08 source capture | Source adapter contracts and synthetic format cases |
| DEP-04 OpenStack target tuple | Platform owner: services/API microversions, backends, network/security realization, image/import permissions and isolated capacity | P00 feasibility, P04 reads, P07/P08 native work | Planning/profile schema and simulator execution |
| DEP-05 Site network and security | Network/security owners: accepted flows, addressing, routing, MTU, ZIP/enforcement, management and failure-domain design | Commissioning; Q05/Q06 native writes/activation | Flow register and negative-case design |
| DEP-06 Shared-service contracts | IPAM/DNS/identity/backup/monitoring owners: authoritative APIs, reservation/release, scoped test credentials and receipts | P07 service readiness and restore; P08 cutover | Adapter contracts and integration doubles |
| DEP-07 Representative application | Product/application/data owners: topology, datasets, acceptance queries, consistency, downtime and recovery acceptance | Initial scope; Q05/Q07 usable service and migration | Generic orchestration only; cannot claim application correctness |
| DEP-08 Secrets, PKI and protected evidence | Security/SRE/records: key custody, secret delivery, retention/residency and access-controlled evidence store | P01 secure runtime; P06/P07 privileged effects | Synthetic trust/retention tests |
| DEP-09 Test capacity and observers | Quality/platform owners: isolated resettable lab, source/target/staging capacity, windows and independent observers | Q02 native coverage; Q05–Q10 | E1/E2 work and campaign preparation |
| DEP-10 Service operation and review | Receiving service/security owners: support responsibilities, recovery targets, reviews, pilot tenant and accepted windows | P10/P11 acceptance | Draft runbooks, exercises in integration and training material |
| DEP-11 Expansion inventory | Product/platform owners: exact P09 tuples, guests/methods and release priorities | P09 estimates; ADR-022 release breadth | Visible unsupported catalogue and preliminary research |

Each live dependency record must include the owner role and named accountable person in the approved working system, requested outcome, acceptance criteria, needed-by milestone, requested/confirmed availability, evidence/reference, fallback consequence and next action. A fallback may reduce scope through an explicit decision; it cannot downgrade a mandatory security or recovery requirement to pass the gate.

## 4. Capacity and performance inputs

P00 defines an initial operating tier and a growth tier. Values remain **selection needed** until product/platform/service owners supply them. Sizing derives from the model and measurements, not the user's whole estate size or a guessed number of pods.

| Input family | Quantities and distribution to capture | Why it affects design |
| --- | --- | --- |
| Tenancy and objects | Active tenants/users, applications, workloads, NICs/disks, policy/dependency edges and revision retention | Authorization/query patterns, index/relationship size and evidence metadata volume |
| Inventory | Sites/endpoints, objects per type, API pages, discovery periods, changes, freshness and allowed native request budgets | Collector concurrency, observation storage, API backpressure and full-generation duration |
| Interactive use | Concurrent sessions, read/edit/approval mix, heavy pages and assessment sizes | End-to-end latency, PHP/API capacity and asynchronous thresholds |
| Jobs and workflows | Submission bursts, concurrent workflows/activities, retries, duration, failure rate and history retention | Temporal/storage/queue capacity, worker limits and fairness |
| Data movement | Dataset bytes/change rate, staging expansion, available bandwidth/IOPS, checksum cost, encryption and transfer windows | Migration feasibility, retained-source/staging reservations and application outage |
| Evidence and telemetry | Artifacts per job, mean/worst sizes, retention, replication, logs/traces and export rates | Object/storage budget, ingestion limits, restore duration and residency |
| Resilience | Failure domains, simultaneous lost capacity, backup/restore throughput, dependency outages and recovery tiers | Surviving eligible capacity, restart budgets and measured RPO/RTO |

Use explicit units and percentile/skew distributions. For example, a lower-bound bulk transfer duration is dataset bytes divided by measured effective bytes/second; capture, conversion, final synchronization, verification and retries add time. A link's nominal bit rate is not effective transfer throughput. Discovery duration depends on both API pages and enforced request rates, and shared endpoint budgets constrain parallel collectors.

Measure with representative synthetic/test data and the selected native tuple, report environment/artifact versions and constraints, and qualify the accepted scale in Q10. Control-plane targets in the phased plan do not become application migration or disaster-recovery commitments automatically.

## 5. Re-estimation triggers and review outcomes

Re-estimate at the P00 scope/feasibility baseline, after P01 reproducible integration, after P06 end-to-end simulation, after the first native Q05 run and at each P09 tranche/release freeze. Re-estimate earlier when:

- The selected migration method fails feasibility or the guest/data/profile scope changes.
- A dependency date passes without accepted access, the lab cannot be reset or an owner/API contract changes.
- Staffing or independent reviewer availability changes enough to invalidate planned concurrency.
- Installed platform/backend/guest versions differ from the qualified baseline or a required security outcome lacks a workable realization.
- Actual campaign duration, failure correction, data growth, API limits or restore throughput contradict the estimate assumptions.
- A new mandatory assurance/residency/disconnected-operation requirement or additional release tuple is selected.

Each review publishes the scope delta, remaining effort/elapsed ranges, evidence behind revised assumptions, changed critical path, external blockers and decision needed. Keep the prior estimate with its date and assumptions so variance is explainable. Update the phased plan only when its programme baseline changes; do not make independent timelines in service documents.
