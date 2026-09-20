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

## Reviewed execution increment

[PR #46](https://github.com/awalker0878/multi-tenant/pull/46) delivers the next
repository implementation in separate commits. Its [execution runbook](terraform-execution.md)
documents the supported operator path and its remaining integration boundaries.

| Delivered capability | Concrete behavior | Remaining boundary |
| --- | --- | --- |
| Private saved-plan preparation | Clean source snapshot, pinned Terraform, explicit HTTP lock endpoints, current contact authority, exact input/credential/trust binding and the existing restricted-plan review | Actual backend, native credentials, accepted target and engineering approval remain external |
| Exact-plan application | Exact bundle/review binding, live expiry checks, backend lock, private logs and source-bound execution | The issuing authority and actual target qualification are not created by JSON records |
| Durable attempt ledger | Persist uncertainty before mutation; reject duplicate operation/generation, concurrent executor writer and unknown prior outcome | A shared durable ledger is required; native tasks and other tools require actual fencing and reconciliation |
| Three-platform credential path | Nutanix/VMware injected credentials; self-contained scoped OpenStack cloud profile; bound optional private CA | Actual least-privilege credentials and supported installed tuples must be supplied and qualified |
| Receipt-based handoffs | Successful exact domain outputs compile disabled workload drafts; successful workload receipts feed pinned guest inventory | Independent native quarantine/placement and VMware network mapping remain required |
| Real local Terraform experiment | Built-in data resource proves saved-plan use, stale-plan rejection, output capture and private artifact permissions | No platform provider, remote backend or infrastructure is exercised |
| Repository release settings | Reviewable required-check/review ruleset and administrator procedure | Settings are not enabled by committing the file; independent reviewer coverage is still needed |

The current Terraform resource modules still describe prepared/restricted state.
Powered/connected native bootstrap, full adopted guest hardening, native drift
repair, upgrades and coordinated retirement remain unfinished. The following
increment implements concrete service operations and edge activation without
silently changing those Terraform lifecycle contracts. W01–W29 remain open under
their actual acceptance criteria.

## Reference service and qualification increment

The [reference decisions](reference-realization.md) choose the internal IPv4
OpenStack fixture as the first qualification path, followed by the other two
required stacks. Product choices now have executable integrations:

| Delivered capability | Concrete behavior | Remaining boundary |
| --- | --- | --- |
| GitLab state configuration | Stable scope-derived HTTP state name and exact lock endpoints | Provision actual service/projects, verify access separation, locking and independent state recovery |
| [NetBox IPAM](netbox-ipam.md) | Reserve/confirm/deprecate exact tenant/VRF/prefix addresses; server ETags, ownership checks, persisted lost-write holds and read-only reconciliation | Actual NetBox 4.7 permissions/concurrency; compute-capacity reservations remain separate |
| [Ubuntu guest services](guest-services.md) | Scoped SSH CA principals/revocation, separate recovery key, explicit resolver, persistent bounded journal and authenticated TLS logging | Trusted images, full selected hardening profile, actual collector receipts, certificate issuance/renewal and native convergence |
| [Backup enrollment and restore](restic-recovery.md) | Confined systemd schedules, disable/withdraw, encrypted file capture and isolated byte-verified restore with separate authority | Server-side append-only/retention, independently recoverable keys and application consistency/acceptance |
| [Edge activation](edge-activation.md) | Exact IPv4 service tuples, atomic scoped nftables table, bootstrap/active/withdraw, kernel lease expiry and established-session withdrawal | Native attachments, same-subnet isolation, route ownership, HA/reboot fail-closed behavior and capacity |
| [Target campaign collector](target-qualification.md) | Native API readback before/after pinned certificate-SSH probes, exact TLS health bytes and healthy controls around denial cases | Execution on actual installed tuples and independent acceptance of the complete campaign |

These are small, separately reviewable commits in PR #46. They do not install a
live service or populate accepted site/platform/assurance indexes. Executable
operations require private actual inputs; documentation examples never supply
native authority.

## Current verification

At `15a574d`, [architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35490547048) and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35490547095) passed. This includes all 16 registered Terraform module/composition/root pairs, real Ansible syntax and local rejection/idempotence checks, and the two disposable packet families. Local Python verification at `9a76d90` passed 1,392 tests and 80 route/model checks; `15a574d` adds the tested ambiguous-input rejection case. Later revisions must use their own exact CI results; these links are not evidence for untested source.

The service/edge revision `0564e8b` passed [architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35512064544) and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35512064540). Its installed engines verified SSH/rsyslog/systemd configuration, real encrypted file recovery and actual nftables packet activation, withdrawal and expiry. The later target-collector and documentation commits require their own exact PR checks; previous passing revisions are not substituted for those checks.

The authoring runtime could not start Terraform provider Unix sockets; GitHub's Terraform engine job supplies the engine evidence. Native Linux convergence/idempotence, platform installation, real remote-state locking, guest bootstrap, actual service enrollment, native failure/restore and retirement have **not** been run. Earlier failed CI runs remain failed records; fixes were committed rather than disabling their gates. Local restic recovery and disposable namespace/SSH experiments are explicitly separate from these native obligations.

## Package disposition and next concrete work

“Partial” credits delivered code or retained functionality, not operational acceptance. “Blocked” identifies missing target/product/authority inputs required for meaningful implementation or execution. Proposed accountable roles remain in the backlog; no individuals or approvals have been invented.

| Package | Current disposition | Work still required to meet acceptance |
| --- | --- | --- |
| W01 | Partial | Replace symbolic environment/cluster examples with actual supported site/cell/platform/API/hardware/licence tuples, image/service offers, owners and first qualification target. Confirm physical mappings and co-residency policy. |
| W02 | Blocked on runner/trust services | Build the selected recoverable native runner, private stores, artifact trust, credential injection/rotation and independent name/time/identity recovery. CI pins alone do not supply P0. |
| W03 | Partial GitLab integration | Scope-specific backend/lock configuration is implemented. Provision the actual GitLab projects, enforce access separation/encryption/versioning, and demonstrate concurrency and independent state restore. |
| W04 | Partial | Core-pinned Linux SSH inventory/profile and guard tests exist. Build the selected execution image, scoped credentials and privileges; prove native convergence/check mode and implement Windows/other offered connection profiles. |
| W05 | Blocked on hardware/fabric selection | Implement actual OOB, firmware, port/underlay/VLAN/VNI/VRF/MTU/HA attachment operations using the selected supported device interfaces; qualify failure and configuration recovery. |
| W06 | Blocked on installed tuples/installers | Select supported Nutanix, VMware/NSX and OpenStack installer/adoption tracks; implement their real inputs, observed readiness and interrupted-install reconciliation. No generic installer stub substitutes for this. |
| W07 | Blocked on service/storage selections | Commission images/templates, entitled pools, storage classes, resolver/time, artifacts, telemetry, identity/PKI and protection consumers; verify bootstrap-to-steady-state transfer. |
| W08 | Partial Linux edge realization | Scoped nftables rules, leases and withdrawal are implemented and locally packet-tested. Commission native ZIP/edge attachments, routing, administrative separation, boot/HA containment and surviving capacity. |
| W09 | Partial placement checks only | Implement actual tenant project/RBAC/quota/pool/AZ entitlement mutations and delegated-credential negative tests. Declared eligibility is not enforced native entitlement. |
| W10 | Partial NetBox IPAM integration | Native API reserve/confirm/retire and uncertain-outcome reconciliation exist. Qualify the actual service, integrate its receipts with accepted records and implement separate compute-capacity hold/renew/release. Address reuse remains held pending cleanup. |
| W11 | Existing DNS tooling; integration open | Bind the selected authoritative DNS operation to real confirmed IPAM/reservation records; qualify A/AAAA/PTR, conflicts, uncertain outcomes, observations and retirement/reuse. |
| W12 | Partial | Compositions, source-bound restricted execution and receipt-based domain/workload/guest handoffs exist. Integrate accepted edge routes/attachments, capacity, IPAM and current native observations; qualify whole fixtures and partial effects on all three stacks. |
| W13 | Partial Linux configuration | Hostname/time/kernel, SSH certificates, resolver and bounded logging exist. Deliver trusted images, first boot/restricted native bootstrap, full adopted hardening, patch/reboot/resume and other offered OS profiles; run native convergence. |
| W14 | Partial selected service enrollment | SSH CA/principals/revocation, TLS log transport and restic schedule/withdrawal exist. Integrate actual issuing/KMS, monitoring, collector acceptance, package and storage services; exercise renewal/revocation and independent restore. |
| W15 | Partial expiring activation | Scoped edge bootstrap/active/withdraw policy and established-session withdrawal are implemented. Connect accepted native attachments, route/reply paths and full readiness authority; qualify boot/HA behavior. Terraform defaults remain restricted. |
| W16 | Partial | Neutron local dispatch and output/inventory binding are added. Implement VM/Nova/Cinder/Flow/category/storage/identity observers and complete receipt-to-manifest integration, using actual task/revision/ETag evidence. Do not invent missing native versions or task IDs from Terraform success. |
| W17 | Blocked on native coordinator/fencing interfaces | Implement actual cross-writer fencing, native task tracking, late/uncertain outcome reconciliation and authorized repair/adoption/cleanup. Serial Ansible and Terraform state locks do not fence native tasks. |
| W18 | Partial operator executor delivered | Plan/apply bundles, bounded native commands, durable uncertainty holds and receipt handoffs are implemented. Integrate the chosen change/automation system with live preflight/reservation, authenticated approval custody, cross-writer fencing, native reconciliation and activation. Provision and recover the actual runner/ledger; no unattended native runner is installed. |
| W19 | Native implementation/qualification open | Decide offered address families. Compiler currently rejects non-IPv4 internal allocations. Deliver native IPv6/dual-stack modules, guest initialization, routes/policy/services and observations for each selected profile; local IPv6 labs are separate evidence. |
| W20 | Collector implemented; actual campaigns pending | Use the bound native/guest collector in restricted campaigns for all three exact installed tuples, complete HA/bypass/capacity tests and independently accept exposure/withdrawal evidence. All native indexes remain unqualified. |
| W21 | Operational integration open | Connect scheduled drift/health/capacity checks to selected observers and alerting, classify emergency/security/unknown drift, and exercise owned incident containment/release. Guest convergence is not a platform drift service. |
| W22 | Lifecycle implementation open | Add accepted resize/scale/growth, image refresh, patch/reboot, provider/platform/collection upgrades, rotation and replacement workflows with actual maintenance budgets and requalification rules. |
| W23 | Partial restic capture/restore | Encrypted scoped file capture, confined scheduling and isolated byte verification are implemented and locally exercised. Provision append-only protection, independent retention/keys, catalogues and application-consistent exports; measure native application RPO/RTO. |
| W24 | Blocked on accepted adoption/recovery design | Deliver exact native import/state mappings, same-service re-creation, supported portable data transitions, and any promised synchronization/cutover/failback with writer exclusion. No blind state move or cross-stack live migration is supplied. |
| W25 | Blocked on retained-data/service authorities | Implement withdrawal and scoped cleanup across policy/routes/DNS/enrollment/native resources; reconcile partial effects, preserve retained copies/keys and release IPAM/reservations only after confirmed cleanup/reuse quarantine. |
| W26 | Partial | Catalogue/provider checks, composition mocks, cluster/inventory negatives, Ansible guards and the real built-in Terraform saved-plan experiment exist. Add actual native operation campaigns, remote backend locking/recovery, service integrations and runtime tests as targets/interfaces are selected. |
| W27 | Maintained docs delivered; operational acceptance open | Current paths, commands, commits and limits are documented. Add actual as-built records, assigned maintaining owners/cadence, accepted operating MOPs and release evidence after qualification. |
| W28 | Conditional; no public profile selected | Select and implement ingress/WAF/LB, PAZ capacity, DNS/certificates, backend identity, HA/recovery and withdrawal; run its independent campaign. Internal OZ/RZ examples do not expose public service. |
| W29 | Conditional; extensions unselected | For each adopted assurance/bare-metal/container/accelerator/stretch/cross-stack/additional-platform offer, supply its design, real automation and separate native evidence/limits. |

## Inputs needed to unblock the integrated build

Provide accepted records through private operator systems, not repository commits containing secrets:

1. Actual first site and lifecycle target; three platform installed tuples and supported installer/adoption choices; native endpoints and scoped access; cluster/host/zone/failure-domain mappings and physical fabric/edge selection.
2. Actual instances/endpoints and custody for the selected GitLab, NetBox, DNS, SSH CA, TLS collector, restic and Linux edge profiles; independently recoverable automation/ledger/key storage; the remaining capacity, storage/image and package/monitoring services.
3. Declared image/OS/address-family/service/recovery offers, change and resource owners, restricted qualification authority, permitted bootstrap paths, and evidence locations.

The reference product choices are already recorded and implemented to the limits above. These private inputs identify real assets and remaining service boundaries; they cannot be inferred from symbolic documentation. Supplying them is not evidence that the work is complete: each package still needs actual execution results and its accepting authority.
