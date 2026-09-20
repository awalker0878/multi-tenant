# Automation implementation progress

**Updated:** 2026-09-20. **Release status:** incomplete; no native platform is qualified by this change. The former `docs/1.0` material is now maintained under engineering, implementation and assurance. The [baseline audit](../../assurance/automation-baseline-audit.md) and its evidence remain historical. Every W01–W29 acceptance package is still open under its [original closure criteria](completion-backlog.md).

## Delivered changes

| Change | Main commit | What is implemented |
| --- | --- | --- |
| Promote the 1.0 documentation | [bf46146](https://github.com/awalker0878/multi-tenant/commit/bf461469d4dc6b1b294d366e6b709d21ad190be7) | Maintained engineering topology, implementation program and assurance audit; repaired links |
| Separate Terraform execution roots | [86105dc](https://github.com/awalker0878/multi-tenant/commit/86105dc8f47cbe5f4bfde021e9ff299b69337911) | `stacks/components`, explicit catalogue, dynamic engine scope discovery; existing component addresses preserved |
| Compose WSD domains and workloads | [79aa0f0](https://github.com/awalker0878/multi-tenant/commit/79aa0f03d3762e9461dd6d9150fbf2c961ed2571) | Six typed compositions and separately owned roots for Nutanix, VMware/NSX and OpenStack; real schema checks and plan-only mocks |
| Update the command-boundary regression | [a6c253a](https://github.com/awalker0878/multi-tenant/commit/a6c253a9f5c071918ec749b23d0b3ca17157ae59) | Backend-free module/composition checks replace the remaining fixed-directory/count assumption |
| Compile cluster placements and output handoffs | [fe08ce4](https://github.com/awalker0878/multi-tenant/commit/fe08ce4e80dfe5d0635716326cc7aa6941bd04bc) | Two-tenant/four-domain examples, role/zone/trust/dedication checks, scoped state identities, disabled draft inputs and matching native output IDs |
| Separate local Ansible profiles | [0c56fb9](https://github.com/awalker0878/multi-tenant/commit/0c56fb9556032109a03a78fe9155557bd234a8e1) | `playbooks/local`, three-platform no-contact manifest validation, real local idempotence/check-mode tests |
| Bind native Linux guest execution | [56e1124](https://github.com/awalker0878/multi-tenant/commit/56e1124afe1c6c1b560b14592f1256c867d0aec8) | Private inventory from workload IDs, pinned SSH keys and observed machine identity; serial Ubuntu 24.04/chrony candidate role with pre-contact guards |
| Correct packet-lab host comparison | [9a76d90](https://github.com/awalker0878/multi-tenant/commit/9a76d908661780bc0126faf25c9f9873b054adec) | Both campaigns compare normalized full host configuration; ordering/lifetimes/counters do not imply drift; addresses/routes/MTUs/forwarding remain checked |
| Tighten private input and guest check mode | [15a574d](https://github.com/awalker0878/multi-tenant/commit/15a574d5eef482ab4ad957e7e8131ff53646d762) | Duplicate JSON keys and non-finite values rejected; live kernel drift explicitly reported in check mode |

Use the [WSD deployment runbook](wsd-deployment.md) and [native guest runbook](native-guests.md) for the actual interfaces, private inputs, output binding and migration precautions. No native apply, guest connection, state migration, activation, deletion or infrastructure deployment was executed during this implementation.

## Current verification

At `15a574d`, [architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35490547048) and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35490547095) passed. This includes all 16 registered Terraform module/composition/root pairs, real Ansible syntax and local rejection/idempotence checks, and the two disposable packet families. Local Python verification at `9a76d90` passed 1,392 tests and 80 route/model checks; `15a574d` adds the tested ambiguous-input rejection case. Later revisions must use their own exact CI results; these links are not evidence for untested source.

The authoring runtime could not start Terraform provider Unix sockets; GitHub's Terraform engine job supplies the engine evidence. Native Linux convergence/idempotence, platform installation, real state locking, guest bootstrap, service enrollment, failure, restore and retirement have **not** been run. Earlier failed CI runs remain failed records; fixes were committed rather than disabling their gates.

## Package disposition and next concrete work

“Partial” credits delivered code or retained functionality, not operational acceptance. “Blocked” identifies missing target/product/authority inputs required for meaningful implementation or execution. Proposed accountable roles remain in the backlog; no individuals or approvals have been invented.

| Package | Current disposition | Work still required to meet acceptance |
| --- | --- | --- |
| W01 | Partial | Replace symbolic environment/cluster examples with actual supported site/cell/platform/API/hardware/licence tuples, image/service offers, owners and first qualification target. Confirm physical mappings and co-residency policy. |
| W02 | Blocked on runner/trust services | Build the selected recoverable native runner, private stores, artifact trust, credential injection/rotation and independent name/time/identity recovery. CI pins alone do not supply P0. |
| W03 | Partial | State-key identities and writer roots exist. Select/provision the backend, map exact addresses/lock endpoints, enforce access separation/encryption/versioning, and demonstrate concurrency and state restore. |
| W04 | Partial | Core-pinned Linux SSH inventory/profile and guard tests exist. Build the selected execution image, scoped credentials and privileges; prove native convergence/check mode and implement Windows/other offered connection profiles. |
| W05 | Blocked on hardware/fabric selection | Implement actual OOB, firmware, port/underlay/VLAN/VNI/VRF/MTU/HA attachment operations using the selected supported device interfaces; qualify failure and configuration recovery. |
| W06 | Blocked on installed tuples/installers | Select supported Nutanix, VMware/NSX and OpenStack installer/adoption tracks; implement their real inputs, observed readiness and interrupted-install reconciliation. No generic installer stub substitutes for this. |
| W07 | Blocked on service/storage selections | Commission images/templates, entitled pools, storage classes, resolver/time, artifacts, telemetry, identity/PKI and protection consumers; verify bootstrap-to-steady-state transfer. |
| W08 | Blocked on security-edge realization | Implement the selected ZIP/edge contexts, attachments, policy, reply paths, administrative separation and HA; qualify no bypass and surviving capacity. |
| W09 | Partial placement checks only | Implement actual tenant project/RBAC/quota/pool/AZ entitlement mutations and delegated-credential negative tests. Declared eligibility is not enforced native entitlement. |
| W10 | Blocked on capacity/IPAM authority | Implement the selected service APIs for idempotent hold/confirm/renew/reconcile/release and exact demand/generation binding. The compiler does not allocate addresses or reserve capacity. |
| W11 | Existing DNS tooling; integration open | Bind the selected authoritative DNS operation to real confirmed IPAM/reservation records; qualify A/AAAA/PTR, conflicts, uncertain outcomes, observations and retirement/reuse. |
| W12 | Partial | Compositions and domain-to-workload ID handoffs exist. Integrate accepted edge routes/attachments, capacity, IPAM, credentials and exact-plan execution; qualify whole fixtures and partial effects on all three stacks. |
| W13 | Partial Linux configuration | Candidate hostname/time/kernel configuration exists. Deliver actual images, provenance, first boot, restricted bootstrap, resolver, full adopted hardening, patch/reboot/resume and selected Windows/other guest profiles. |
| W14 | Blocked on consumer interfaces | Implement selected identity/certificate/KMS, monitoring/logging, backup, storage and package enrollment/renewal/revocation/removal with actual service replies and restore evidence. |
| W15 | Blocked on edge/service handoffs | Implement approved connectivity, scoped allow rules, forward/reply routing and controlled egress/activation field ownership. Current Terraform resources remain restricted. |
| W16 | Partial | Neutron local dispatch and output/inventory binding are added. Implement VM/Nova/Cinder/Flow/category/storage/identity observers and complete receipt-to-manifest integration, using actual task/revision/ETag evidence. Do not invent missing native versions or task IDs from Terraform success. |
| W17 | Blocked on native coordinator/fencing interfaces | Implement actual cross-writer fencing, native task tracking, late/uncertain outcome reconciliation and authorized repair/adoption/cleanup. Serial Ansible and Terraform state locks do not fence native tasks. |
| W18 | Runbooks and handoffs delivered; coordinator open | Integrate the chosen change/automation system with live preflight/reservation, exact saved-plan/source/input binding, ordered apply, evidence retention, native reconciliation and activation hold. No unattended native runner is installed. |
| W19 | Native implementation/qualification open | Decide offered address families. Compiler currently rejects non-IPv4 internal allocations. Deliver native IPv6/dual-stack modules, guest initialization, routes/policy/services and observations for each selected profile; local IPv6 labs are separate evidence. |
| W20 | Blocked on real targets and prerequisites | Execute and independently accept restricted native campaigns for all three exact tuples, publish measured capacity and demonstrate controlled production exposure/withdrawal. All native indexes remain unqualified. |
| W21 | Operational integration open | Connect scheduled drift/health/capacity checks to selected observers and alerting, classify emergency/security/unknown drift, and exercise owned incident containment/release. Guest convergence is not a platform drift service. |
| W22 | Lifecycle implementation open | Add accepted resize/scale/growth, image refresh, patch/reboot, provider/platform/collection upgrades, rotation and replacement workflows with actual maintenance budgets and requalification rules. |
| W23 | Blocked on backup/key/storage products | Implement capture/retention and isolated useful-data restore against the selected services, independent protection/delete authority, catalogues/keys and measured RPO/RTO. |
| W24 | Blocked on accepted adoption/recovery design | Deliver exact native import/state mappings, same-service re-creation, supported portable data transitions, and any promised synchronization/cutover/failback with writer exclusion. No blind state move or cross-stack live migration is supplied. |
| W25 | Blocked on retained-data/service authorities | Implement withdrawal and scoped cleanup across policy/routes/DNS/enrollment/native resources; reconcile partial effects, preserve retained copies/keys and release IPAM/reservations only after confirmed cleanup/reuse quarantine. |
| W26 | Partial | Catalogue-based Terraform checks, composition mocks, cluster/inventory negatives and native Ansible guard checks exist. Add actual native operation campaigns, service integrations, secrets controls and runtime tests as targets/interfaces are selected. |
| W27 | Maintained docs delivered; operational acceptance open | Current paths, commands, commits and limits are documented. Add actual as-built records, assigned maintaining owners/cadence, accepted operating MOPs and release evidence after qualification. |
| W28 | Conditional; no public profile selected | Select and implement ingress/WAF/LB, PAZ capacity, DNS/certificates, backend identity, HA/recovery and withdrawal; run its independent campaign. Internal OZ/RZ examples do not expose public service. |
| W29 | Conditional; extensions unselected | For each adopted assurance/bare-metal/container/accelerator/stretch/cross-stack/additional-platform offer, supply its design, real automation and separate native evidence/limits. |

## Inputs needed to unblock the integrated build

Provide accepted records through private operator systems, not repository commits containing secrets:

1. Actual first site and lifecycle target; three platform installed tuples and supported installer/adoption choices; native endpoints and scoped access; cluster/host/zone/failure-domain mappings and physical fabric/edge selection.
2. State and automation services with recovery/ownership design; capacity, IPAM and DNS authority APIs; selected storage, image, trust, package, telemetry and protection services and their consumer interfaces.
3. Declared image/OS/address-family/service/recovery offers, change and resource owners, restricted qualification authority, permitted bootstrap paths, and evidence locations.

These inputs are required to implement and test the remaining product-specific integrations. Supplying them is not evidence that the work is complete; each package still needs its source, actual execution results and accepting authority.
