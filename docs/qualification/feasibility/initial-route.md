# Initial VMware-to-OpenStack route feasibility

This procedure supports P00.04, R01 and G00.04. Its purpose is to decide whether the selected first application can use the proposed offline migration method and what implementation must prove. It does not qualify a production route. The method decision belongs to ADR-014 in the [decision register](../../decisions/decision-register.md); full native qualification uses [Q07](../campaigns/q07-first-offline-migration.md).

## Candidate and decision boundary

The candidate is the synthetic [Permit Desk](../../product/application-walkthrough.md) application: one Linux web workload, one Linux database workload, database records and attachment data, separate OZ/RZ placements and declared shared-service dependencies. The initial method proposal is cold VMware guest/disk capture, conversion and OpenStack import. Application rebuild/restore is a distinct alternative requiring an explicit method decision and revised acceptance scope.

Record the source/target installation, backend and enabled-feature identities; guest image and architecture; firmware and device model; all disks, snapshots and backing chains; NIC/address mapping; network enforcement path; application consistency model; encryption/key references; staging and retained-source requirements. Unknown fields remain open feasibility inputs. A vendor name or working VM export is insufficient to freeze this tuple.

## Inputs and responsibilities

| Input | Required content | Accountable role |
| --- | --- | --- |
| Native facts | Read-only inventory, installed/API/backend versions, disk/device details, source IDs and privileges | VMware/OpenStack platform owners |
| Application fixture | Dataset manifest, consistent capture procedure, dependencies, correctness queries and business-effect suppression | Application/data owner |
| Authority scope | Permitted reads, isolated fixture changes, resource limits, endpoints, campaign stop and cleanup authority | Platform and security owners |
| Acceptance measures | Allowed outage/data change, measured transfer/staging budget, target readiness and recovery conditions | Application and SRE owners |
| Independent review | Observer access and evidence custody, including conversion-output and key restrictions | Qualification and security leads |

## Assessment sequence

1. Inventory every workload, disk, NIC, dataset and external writer. Reconcile the logical application manifest to native identities. Explain any unmatched or shared resource before selecting a capture boundary.
2. Trace boot dependencies: BIOS/UEFI, secure-boot requirements, boot partitions, controller drivers, root-device naming, initialization and guest identity. Classify each as preserved, explicitly transformed or unsupported for the candidate method.
3. Examine disk chains, shared/multi-attach usage, special devices, encrypted disks, vTPM dependencies and passthrough. A constraint without a demonstrated treatment blocks the affected scope; it cannot disappear from the profile.
4. Design a transactionally consistent dataset capture. Include database state, attachments, permissions/metadata and required keys. Define how background workers, scheduled jobs and external writers are stopped or fenced.
5. Design the target mappings and quarantine. Preserve application-required semantics while explicitly approving changed native identities, addresses, failure-domain placement and network policy realization.
6. Run bounded conversion/import experiments only on approved fixtures. Record commands actually executed, tool/artifact versions, source/output digests, measured resource use and boot/application observations. Preserve failures and recovery attempts.
7. Repeat interrupted transfer/conversion and invalid-image cases. Determine whether the method supports safe resume, requires full restart or leaves a cleanup obligation; bind the behavior into the plan design.
8. Model the pre-target-write rollback and post-target-write recovery separately. Demonstrate a small stateful experiment for the proposed divergence treatment where authorized; otherwise record exactly which experiment blocks the decision.
9. Review results with platform, application, security and qualification owners. Accept the bounded candidate, require a specific additional experiment, select a different method explicitly or reject the route.

## Feasibility checks

| Check | Required observation | Implementation consequence |
| --- | --- | --- |
| F01 — Complete capture | Every dataset and boot dependency appears in the manifest and consistency boundary | Missing data blocks method acceptance |
| F02 — Boot and identity | Approved converted fixture boots with declared drivers and expected application/guest identity treatment | Add explicit transformation or exclude unsupported profile |
| F03 — Data correctness | Record set, attachment digests, metadata and relationships match the captured consistent source | Differences require investigation before route selection |
| F04 — Isolation | Rehearsal target cannot send production mail, trigger jobs or receive production traffic | Add enforced isolation and business-effect controls |
| F05 — Resource budget | Capture, transfer, conversion, import and retained source fit measured storage/bandwidth constraints | Revise placement/budget or reject candidate |
| F06 — Recovery boundary | Source can remain fenced; target writes are identified; accepted writes have a defined preservation path | No post-write recovery mechanism means no migration commitment |
| F07 — Unsupported features | Every relevant guest/storage/network/device feature has a tested treatment or explicit exclusion | Profile and UI must block affected requests |

## Decision record

Record the exact candidate tuple and fixture provenance, observed findings by F01–F07, tested and untested assumptions, evidence IDs, method decision, exclusions, required implementation and Q07 cases. Identify actual reviewers and dates only when review occurs. E0 documents the assessed design; E1/E2 describes actual bounded experiments at their true environment level. Read-only native observations cannot alone establish native migration support.

For unresolved access or input, record its responsible role, required fact or experiment, unblock condition and next action in the delivery register. G00.04 cannot pass on an untested route assertion. Preserve useful contract work while the bounded feasibility question is resolved.

## Retest triggers

Reassess affected findings when the selected method, platform/backend, guest image, firmware, disk/encryption design, dataset consistency mechanism or recovery strategy changes. Carry forward an unaffected finding only with a scoped impact review; never transfer qualification from the earlier branch.
