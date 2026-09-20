# Portable Multi-Tenant Secure Hosting

Infrastructure architecture, engineering and implementation workspace. This repository is public; actual inventories, credentials, plans, state and native evidence belong in private operator systems.

## Read the architecture and engineering in Git

The Word library is now available as full linked Markdown chapters, tables, diagrams and working templates—not only a list of attachments.

| Area | Start here |
| --- | --- |
| Complete documentation | [Documentation home](docs/README.md) |
| Reference architecture / RAD | [Architecture](docs/architecture/README.md) · [RAD reading view](docs/architecture/RAD.md) |
| Technical architecture / TAD | [Engineering](docs/engineering/README.md) · [TAD reading view](docs/engineering/TAD.md) |
| Solution design | [Service decisions and worked infrastructure](docs/solutions/README.md) |
| Architecture decisions | [Proposed ADR register](docs/adr/README.md) |
| Implementation | [Commissioning and code map](docs/implementation/README.md) |
| Assurance and audit | [Requirements, qualification and source audits](docs/assurance/README.md) |
| Operations and working forms | [Operations](docs/operations/README.md) · [HLD/LLD/MOP templates](docs/templates/README.md) |
| Provenance and original artifacts | [Migration record](docs/DOCUMENTATION_MIGRATION.md) · [Source files and workbooks](docs/ARTIFACT_CATALOG.md) |

## Implementation boundaries

The infrastructure architecture remains authoritative. Terraform and Ansible implement separately owned resource and verification responsibilities; they do not define a new hosting application. Native code remains candidate implementation until its actual supported target and evidence are accepted. The supplied source records distinguish local fixtures, native readback and formal operating authorization.

The ten native Terraform primitives are retained under `terraform/modules`; their execution roots now live under `terraform/stacks/components`. Six WSD compositions add separate domain and workload roots under `terraform/stacks/wsd`. Cluster-aware input compilation and a bound Linux guest Ansible profile connect those scopes without changing the native quarantine defaults. The integrated audit correction preserves production connectivity and resource semantics. Current source publication is recorded by Git and exact CI results; ZIP-era statements describe their original delivery only. Historical test reports remain historical, and no infrastructure is deployed by this repository review.

## Current automation delivery

The former `docs/1.0` plan now lives in the maintained [automation delivery program](docs/implementation/automation/README.md). Use the [WSD deployment runbook](docs/implementation/automation/wsd-deployment.md), [native guest runbook](docs/implementation/automation/native-guests.md) and [package delivery record](docs/implementation/automation/progress.md). Site commissioning, service-owner integrations, complete lifecycle automation and native qualification remain incomplete; repository publication is not an end-to-end release.

[Reviewed Terraform execution](docs/implementation/automation/terraform-execution.md) supplies private saved-plan preparation/application, exact source/input/backend/credential binding, durable failure holds, and execution-receipt handoffs into workload compilation and guest inventory. The [release controls](docs/implementation/automation/release-controls.md) include a proposed GitHub ruleset and its administrator activation steps. Neither addition qualifies a native platform or activates production.

The [reference implementation](docs/implementation/automation/reference-realization.md)
now selects an OpenStack-first internal IPv4 qualification path, GitLab state,
NetBox IPAM, Ubuntu certificate SSH/resolver/TLS logging, restic protection and a
provider-owned nftables edge. Executable adapters perform scoped allocation,
guest enrollment, encrypted file capture/restore, expiring activation and
established-session withdrawal. The [target runner](docs/implementation/automation/target-qualification.md)
collects real API and guest traffic evidence. Actual site commissioning, full
platform lifecycle and independent native acceptance remain required.

The [restricted platform lifecycle](docs/implementation/automation/platform-lifecycle.md)
now includes owned Nutanix Flow service bootstrap/withdrawal and exact-plan checks.
[Flow snapshots](docs/implementation/automation/nutanix-flow-readback.md) bind policy,
category and VPC evidence to AHV guest campaigns. [vSphere readback](docs/implementation/automation/vsphere-readback.md)
adds VM/device/placement snapshots and bounded task-tree/child-history observations,
including accepted template identities and exact clone result VMs,
alongside NSX campaigns. [Held-attempt review](docs/implementation/automation/terraform-recovery.md)
compares supported existing-VM configuration with the saved plan and binds the
durable ledger without releasing it. Clone state adoption remains separate.
Live commissioning, effective enforcement, complete fenced native
reconciliation and HA/application recovery qualification remain open.

## Local review

```sh
python -m pip install -r requirements-repository.txt
python scripts/check_documentation.py
python scripts/check_repository.py
python tools/check_local.py
```

See [TESTING.md](docs/TESTING.md) for independent Terraform/Ansible and disposable-lab gates. Read the exact CI revision for actual engine and local packet results; none of those checks qualifies a native platform. See [LOCAL_IMPORT.md](docs/LOCAL_IMPORT.md) before importing into your own checkout.

## Completion-audit corrections

[Corrective disposition register](docs/assurance/completion-corrections.md) records code-fidelity, semantic-negative, current-integrity, ADR lifecycle, test-family and assertion-allocation work. [Maintained design records](docs/current/README.md) are distinct from immutable Word transcriptions. Actual initial Terraform/Ansible engine results and provider locks are recorded in [engine evidence](evidence/completion-corrections/README.md); final-revision CI and native qualification are separate gates.

## Current main integration follow-up

[Main integration audit](docs/assurance/main-integration-audit.md) records the mixed-correction test failures and their canonical-record resolution. The complete regression suite remains required alongside real Terraform/Ansible checks; no failing tests are skipped and no native acceptance is issued.

## Routed IPv6 implementation work

The [I08 packet extension](docs/implementation/routed-ipv6-lab.md) exercises the existing WD14 topology over real IPv6 sockets in disposable Linux namespaces. Its [engineering profile](docs/engineering/routed-ipv6-qualification.md) distinguishes local path evidence from the still-open native platform and offered-family acceptance. Exact current run results belong to CI artifacts, not historical reports.

## Known native task-tree verification

The [I09 Nutanix task-tree extension](docs/implementation/nutanix-task-tree-readback.md) observes explicitly recorded parent/child work without discovery, cancellation or mutation. Its [engineering profile](docs/engineering/nutanix-task-tree-readback.md) keeps incomplete children, failed tasks, native resource differences and actual fencing obligations separate from a successful parent label.

## Platform capability evidence

The [machine-readable platform capability registry](docs/engineering/platform-capability-registry.md) records candidate implementation coverage separately from native qualification. Current entries fail closed for placement because no installed platform tuple has completed native qualification; local source or fixtures are not promoted to production capability evidence.


## Pre-placement platform-family eligibility

The [platform-family eligibility precheck](docs/engineering/pre-placement-platform-eligibility.md) consumes a reviewed WSD engineering reference plus mandatory/optional portable capabilities and fails closed when no candidate family is natively qualified. It does not choose a site, reserve capacity, allocate infrastructure, run Terraform, or authorize activation. The repository example is intentionally held until native platform qualification exists.


## Native PlatformProfile qualification

The [native qualification dossier](docs/engineering/platform-native-qualification.md) binds an exact product/API/provider/hardware tuple to tested capabilities, assurance profiles, limits, current evidence, owners and a controlled approval reference. Every native evidence entry must now trace to current latest-passing evidence from a target-bound qualification campaign packet with matching digest/observation time, and dossier validity cannot outlive the campaign evidence freshness. The active qualification index is intentionally empty; registry claims cannot become `NATIVE_QUALIFIED` merely by editing the capability file. Production authorization remains separate.


## Site and service-class capacity eligibility

The [site/service capacity precheck](docs/engineering/site-service-capacity-eligibility.md) evaluates current commissioned envelopes against required profiles, the accepted failure model, surviving capacity, operational reserve, commitments, unavailable capacity and supplied quota headroom. The active inventory is intentionally empty. A match identifies candidate envelopes only; it does not select a site, reserve capacity, allocate addresses, run Terraform or authorize activation.


## Reservation preflight and reconciliation

The [reservation preflight](docs/engineering/reservation-preflight-and-reconciliation.md) binds stable reservation/operation identities, generation, exact admitted demand, owner roles and expiry to exported records from the authoritative reservation system. Git remains evidence-only: same-operation retries are idempotent only when the spec is unchanged, conflicts and uncertain outcomes stop, and IPAM/external reservations remain under their own owners. No reservation is created or released by CI.


## Authoritative IPAM allocation handoff

The [IPAM allocation handoff](docs/engineering/authoritative-ipam-allocation-handoff.md) binds the parent reservation's stable IPAM dependency operation to exported authoritative allocation lifecycle evidence. Git stores no actual address/prefix value: unique allocation is the default, overlap requires an explicit exception reference, uncertain outcomes stop retries, and release requires route/DHCP/DNS/policy/logging/incident-response cleanup plus reuse quarantine. Actual IPAM mutation remains external.


## Authoritative DNS registration handoff

The [DNS registration handoff](docs/engineering/authoritative-dns-registration-handoff.md) binds an immutable DNS operation to the stable SHA-256 of a confirmed authoritative IPAM allocation/realization and to the SHA-256 of the complete normalized DNS intent. Reused allocation/registration IDs cannot hide parent, TTL, zone, owner or scope drift. Git stores no actual FQDN or A/AAAA/PTR value. Required propagation observations remain explicit, retirement preserves tombstone/reuse controls, and the RFC2136 client remains a separately approved service-owner mutation path never invoked by CI.


## Backup protection and isolated-restore assurance

The [backup/restore assurance gate](docs/engineering/backup-isolated-restore-assurance.md) requires evidence of management separation, protected-copy retention, catalogue/key availability and a current isolated useful-data restore before the backup/recovery dependency can be considered ready. The active assurance index is intentionally empty. CI captures and restores only disposable local fixture files; it never accesses native backup data, destroys retained keys, reconnects a restored service or authorizes production.

## Control inheritance and external-dependency assurance

The [control inheritance assurance gate](docs/engineering/control-inheritance-and-external-dependency-assurance.md) makes G30 fail closed until the exact WSD/site/service/platform/control-selection scope has reviewed provider/tenant/shared/inherited allocations, current evidence for all six organizational interfaces, and no unresolved residual control gaps. The active assurance index is intentionally empty. CI cannot select controls, accept inherited evidence or residual risk, issue authorization, apply infrastructure or activate production.

## Operational handover and incident-readiness assurance

The [operational handover assurance gate](docs/engineering/operational-handover-and-incident-readiness-assurance.md) makes G31 fail closed until the exact operating scope has attributable receiving/support/on-call ownership, privileged-access and monitoring reviews, explicit incident containment/release authority, and a current scoped incident exercise with emergency-change reconciliation. The active assurance index is intentionally empty. CI cannot change access, start or release containment, execute recovery, reconcile a live emergency change, apply infrastructure or activate production.

## Version, source provenance and lifecycle assurance

The [version/source provenance gate](docs/engineering/version-source-provenance-and-lifecycle-assurance.md) makes G32 fail closed until an exact product/API/provider/hardware/licence tuple has current official support/source reviews, dated compatibility evidence and lifecycle ownership. Source edition and review state remain separate, partial or inherited references cannot satisfy current support, and native qualification now requires a matching CURRENT_SUPPORTED provenance record. The active provenance index is intentionally empty.

## Bounded extension adoption and qualification assurance

The [extension adoption gate](docs/engineering/bounded-extension-adoption-and-qualification-assurance.md) makes G33 fail closed for bare metal, container hosting, accelerators/special devices, L2-stretch/cross-stack patterns, higher-assurance designs and future platforms. Every accepted record remains `EXTENSION_ONLY` and requires complete topology/lifecycle design, all qualification dimensions, kind-specific evidence, explicit unsupported capabilities and no unresolved gaps. The active extension index is intentionally empty.

## Knowledge maintenance and release-integrity assurance

The [knowledge-maintenance gate](docs/engineering/knowledge-maintenance-and-release-integrity-assurance.md) makes G34 fail closed beyond static link checking. It validates the eight source-derived primary knowledge homes and requires revision-specific version-set evidence, maintaining owner/cadence, release-wide link/requirement/decision consistency, duplicate-policy and parent/supplement drift review, change-ripple review and an approved change record. The active release-maintenance index is intentionally empty.

## Security-edge and ZIP assurance

The [security-edge ZIP gate](docs/engineering/security-edge-zip-assurance.md) addresses the remaining I03/I04 native boundary dependency. A current ZIP requires an exact pairwise boundary, both adjacent authorities, joint approval, deny-first policy, native forward/reply and bypass review, inspection/logging/session evidence, management separation, HA/failure tests and measured survivor capacity. Distributed/shared realizations must prove equivalent mandatory outcomes. The active ZIP assurance index is intentionally empty.

## Native readback, writer-fencing and reconciliation assurance

The [native reconciliation gate](docs/engineering/native-readback-writer-fencing-and-reconciliation-assurance.md) addresses I09 above the existing NSX, Nutanix and Neutron read-only observers. A matching readback is insufficient: current readiness also requires exact installed API/RBAC/default/version-token applicability, complete task/entity coverage, true scoped writer fencing, current containment state, exact operation generation and an attributable data-safe reconciliation decision. The active reconciliation index is intentionally empty and CI cannot list/cancel tasks, release containment, import state, repair, delete, apply or activate.

## Native IPv6 and address-family assurance

The [native IPv6 assurance gate](docs/engineering/native-ipv6-address-family-assurance.md) addresses I08 above the routed Linux laboratory. A current IPv6-only or dual-stack service requires exact site/platform/security-edge scope, supported addressing/local-protocol behavior, route/security parity, MTU/PMTU evidence, required shared-service paths, failure/recovery evidence and operational acceptance. IPv6-only must prove no hidden IPv4 fallback; dual-stack must retain an independent IPv4 campaign. The active native IPv6 assurance index is intentionally empty.

## Production activation and initial-readiness assurance

The [production activation gate](docs/engineering/production-activation-and-initial-readiness-assurance.md) addresses I10 without granting activation authority. It binds exact site/service/platform/workload/exposure scope to current G0/G1/G2 prerequisites, applicable initial G4 recovery/operations readiness, valid operating authority, a reversible G3 exposure plan, tested withdrawal readiness, and post-activation live-path evidence. Failed or unknown live verification requires withdrawal rather than optimistic continuation. The active activation index is intentionally empty.

## Identity, certificate and cryptographic trust assurance

The [identity/crypto trust gate](docs/engineering/identity-crypto-trust-assurance.md) addresses the trust-services portion of I07. It requires separately scoped human/workload/automation identities, hardened privileged/emergency access, observed revocation including cached tokens, certificate issuance/renewal/revocation and endpoint identity, separated key-use/admin/recovery/destruction authority, retained-data-aware destruction, KMS/trust outage behavior, no plaintext fallback, independent recovery and crypto-agility records. The active trust index is intentionally empty.

## Storage ownership, copy-lineage and lifecycle assurance

The [storage lifecycle gate](docs/engineering/storage-data-lifecycle-assurance.md) addresses the remaining storage-service portion of I07. It requires current owner/categorization/access/key/placement lineage, cross-scope authorization and denial evidence, measurable capacity/performance/consistency/replication/snapshot/portability semantics under contention and failure, authoritative derivative-copy/hold/key-version records, and a qualified withdrawal/sanitization/receipt procedure. Backup/restore remains a separate assurance dependency. The active storage index is intentionally empty.

## Origin-specific shared-service reply assurance

The [service-reply assurance gate](docs/engineering/origin-specific-service-reply-assurance.md) addresses I05 above the routed packet fixture. A current binding requires exact service entitlement, endpoint identity/authentication, forward and origin-specific reply ownership, accepted ZIP evidence, connected/summary/NAT/PBR/alternate-interface review, source validation, no-transit proof, missing-reply-route and edge-failure tests, reverse-initiation denial, recovery, telemetry, survivor capacity, and binding/version revocation evidence. The active service-reply index is intentionally empty.

## Bootstrap service and steady-state transition assurance

The [bootstrap service gate](docs/engineering/bootstrap-service-readiness-assurance.md) addresses I06 by composing the existing authoritative IPAM/DNS handoffs with the minimum initialization dependencies required for safe Day-0 and endpoint bootstrap. Current readiness requires selected address-assignment/DHCP-metadata behavior, resolver/time/trust/certificate/key/artifact/telemetry/service-reply paths, restricted OOB/management execution, dependency-loss behavior with no unrestricted fallback, recoverable configuration/state, and verified transition from temporary dependencies to steady-state services. The active bootstrap index is intentionally empty.

## Actual target selection for restricted native campaigns

The [target-selection assurance gate](docs/engineering/actual-target-selection-assurance.md) addresses I02 without choosing a site, platform or security edge. A current record captures the externally selected site/cell, exact installed tuple references, EC/SE realization, restricted native API/observer/writer scope, credential custody, evidence workspace, data restrictions, permitted/prohibited operations, cleanup/stop authority and time-bounded target-contact authority. The active target-selection index is intentionally empty, and CI cannot select or contact a target.

## Qualification campaign evidence assurance

The [campaign evidence gate](docs/engineering/qualification-campaign-evidence-assurance.md) binds an externally executed native qualification campaign to the reviewed target, exact service/topology scope, and the selected change/contact/stop authority, native API/observer/writer scopes, credential custody, evidence workspace, data restrictions, permitted/prohibited operations, cleanup and contact window. Attempts after the authorized contact expiry are rejected. Evidence collected inside a valid window may remain reviewable after contact authority later expires, but no reconnect or retest authority is implied. The gate also requires explicit applicability, retained attempts, healthy positive controls for negative observations, artifact hashes, freshness, reviewed not-applicable decisions and residual-gap state. The active campaign evidence index is intentionally empty.
