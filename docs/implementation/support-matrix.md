# Capability scope and support publication

**Baseline: no product operation or native platform tuple is qualified or operationally accepted.** This is a planning matrix for the greenfield product, not a support announcement. The proposed first path is selected OpenStack/Linux provisioning followed by a conditional VMware-to-OpenStack offline migration. No previous branch's evidence transfers.

This document owns intended support scope and publication rules. The [requirements register](requirements-and-qualification.md) owns requirement semantics and the complete profile dimensions; the [delivery register](delivery-register.yaml) owns execution status/evidence references under the [status model](status-model.md). Actual campaign evidence and assurance decisions belong in their protected evidence system. Do not copy changing qualification or acceptance flags into this planning table.

## 1. Interpreting the matrix

"Initial candidate" means selected for design and feasibility, not available software. "Expansion candidate" means a separately scoped P09 or later tranche, not a release promise. "Deferred" means outside the initial release unless ADR-022 explicitly changes its scope and the required implementation/qualification gates are met. Unknown capability remains unknown; it is not treated as an optional passing condition.

Before operational admission, a support record must match the exact operation tuple and current release, carry current E3 qualification, and satisfy the operating release's E4 acceptance conditions. Qualification is neither a tenant grant nor approval of a plan. An isolated qualification campaign uses ADR-018 lab authorization; it does not publish the tested candidate automatically.

## 2. Lifecycle scope

| Capability | Planned platform/guest scope | Planned first delivery | Conditions and required campaign |
| --- | --- | --- | --- |
| Platform profile contracts | VMware, Nutanix AHV and OpenStack; every required dimension visible | P04/P05 | R09/R13; Q02/Q03; a complete schema does not imply collectors or native features are qualified |
| Read-only discovery | All three contracts; initially selected installed source/target tuples | P04; additional native tuples P09 | Commissioned collector, scoped authority, paging/completeness/freshness and independent readback; Q02 |
| Assessment and planning | Candidate destinations with pinned observations/profiles | P05 | Unknown or unsupported mandatory outcomes block eligibility; Q03; simulated comparisons are E2 only |
| Create and activate | Selected OpenStack installation, one approved Linux image and representative multi-workload application | P07 initial candidate | R18–R21; Q04/Q05/Q06; actual networking, guest, DNS/IPAM, identity, monitoring and backup/restore prerequisites |
| Managed change / power / resize / replace | Each operation separately selected for initial OpenStack scope | P07 selected operations; later breadth P09 | Exact mutation, field ownership, failure and recovery evidence; generic "lifecycle supported" is insufficient |
| Retire managed resources | Selected OpenStack provisioned resources and later retained migration source as separately authorized | P07/P08 | R25; Q05/Q07; retention, keys, disposal, address/identity release and independent cleanup receipt |
| Brownfield adoption | Selected exact objects/fields on separately chosen tuples | P09 expansion candidate | R11; observation-only first, writer/ownership transfer and no-change import proof; Q02/Q08 |
| Recovery / HA | Product and selected workload failure models | Incremental P01–P08; full campaign P10 | R29; Q04/Q05/Q07/Q09; control-plane restore, native service HA and application recovery are distinct claims |
| Waves / concurrent operations | Approved release workload mix and endpoint/risk budgets | P09/P10 expansion candidate | R28/R34; Q10; concurrency requires capacity/fairness/stop evidence and cannot be inferred from a single job |

Admission rejects any unlisted exact operation/tuple rather than interpreting an implemented adapter as blanket support. Selecting only a subset of managed-change operations requires an explicit release scope and documented limitations; it does not remove enterprise requirement coverage from the backlog.

## 3. All six cross-platform directions

Each direction below needs its own method, guest, data and recovery qualification. Reverse direction is never inherited. Even when the same conversion tool is used, source capture, target import, policy realization, drivers and post-write recovery can differ.

| Source → target | Planning scope | Method selection | Required qualification before a support claim |
| --- | --- | --- | --- |
| VMware → OpenStack | Initial candidate, P08 | `native_api_export_import` through ExportVm/NFC and destination native APIs | Q07 for exact source/target/guest/data/security/service tuple; all disks, native import, firmware/drivers, writer fencing, application checks and post-target-write recovery |
| OpenStack → VMware | Expansion candidate, P09 or later | Selection needed; no reverse-method assumption | Q08 independently covering export/import or selected restore method, target policy/service realization and recovery |
| VMware → Nutanix AHV | Expansion candidate, P09 or later | Selection needed | Q08 independently covering source/target mapping, selected method, guest/data and recovery |
| Nutanix AHV → VMware | Expansion candidate, P09 or later | Selection needed | Q08 independently; VMware→AHV results are not evidence for this direction |
| OpenStack → Nutanix AHV | Expansion candidate, P09 or later | Selection needed | Q08 independently covering storage/network/guest transformations and application checks |
| Nutanix AHV → OpenStack | Expansion candidate, P09 or later | Selection needed | Q08 independently; OpenStack provisioning alone does not qualify migrated guest/data state |

Same-family VMware→VMware, AHV→AHV and OpenStack→OpenStack movement are separate topology-specific candidates. A cross-site, cross-cluster, cross-version or different backend move is not automatically native live migration. Same-family routes need recorded source/target tuples, method and independent evidence when advertised.

P00 selects only one initial offline method; application rebuild/restore is preferred. Cold capture/conversion/import is separately evaluated in P09 for applications that cannot be rebuilt, with disk-chain, boot, device, driver and encryption checks. If either method is infeasible, record why and approve the changed scope explicitly before substituting the other. Neither method proves warm/live migration, zero downtime or universal guest portability.

## 4. Guest, data and special-feature scope

These dimensions compose with every operation and route; a row is never a standalone support claim.

| Variant | Initial scope | Required selection or later work |
| --- | --- | --- |
| Linux standard guest | Initial candidate: one selected distribution/version/image, architecture, firmware and driver profile | Exact image provenance, hardening, device/boot/network readiness and restore checks; Q05/Q07 |
| Additional Linux distributions/versions | Deferred unless selected | Separate compatibility/qualification scope; no inference from one distribution |
| Windows | Expansion candidate | Selected versions, licensing/image provenance, firmware, drivers, identity/Sysprep behavior, encryption and application checks; R27/Q08 |
| Appliance / no guest mutation | Expansion candidate | Vendor-supported import/export, immutable guest constraints, licensing and external readiness/health contract; R27/Q08 |
| Stateful application dataset | Initial candidate: explicitly selected application and consistency rules | Dataset inventory, transaction consistency, metadata/keys, final sync, integrity, writer fencing and divergence recovery; R22–R24 |
| Multi-VM/disk/NIC application | Selected initial representative path | Explicit dependency/order, mappings, consistency groups and failure-domain constraints; R19; complexity bounded in P00 |
| Rebuild / application restore | Preferred initial P08 method, conditional on P00 feasibility | Reconstruction completeness, configuration/secrets and every approved dataset; not proof of whole-VM conversion |
| Database replication / warm synchronization | Deferred expansion | Engine/version-specific consistency, lag, writer handoff, split-brain prevention and target-write recovery |
| Warm/live movement / zero downtime | Deferred | Separate implementation, topology/API support, measured outage and failure/recovery evidence |
| UEFI / BIOS / secure boot / vTPM / encrypted disks | Only exact selected initial values | Unsupported or unassessed combinations block placement; keys, attestation and imported boot behavior need specific evidence |
| Shared/multi-attach disks, GPU, passthrough or architecture changes | Deferred unless explicitly selected | Separate platform/guest/device feasibility, ownership, data and recovery qualification |
| IPv6, overlapping addresses and alternate edge/service integrations | Requirement-driven exact selection | Explicit values in every profile; required unsupported controls block the route, not silently disappear |

## 5. Complete profile coverage and requirement mapping

The [canonical capability dimensions](requirements-and-qualification.md#3-complete-profile-dimensions-for-all-three-platforms) define the required fields. The mapping below helps find the engineering obligations; it does not replace that definition or claim any dimension is complete. Every VMware, AHV and OpenStack profile must represent every row, including explicit unknown/unsupported constraints.

| Canonical dimension | Principal requirement references | Where evidence is first exercised |
| --- | --- | --- |
| Installed identity | R08–R10, R13, R35 | Q02/Q03; exact tuple rerun for releases |
| Compute and placement | R08, R12–R13, R17–R19, R34 | Q03/Q05; capacity/failure expansion Q08/Q10 |
| Storage and datasets | R13, R17, R19, R21–R25 | Q05/Q07/Q08 |
| Network and tenant VPC | R06–R08, R13, R19–R20 | Q03/Q05/Q06 |
| Security and edge | R03–R04, R07–R08, R13, R20, R31–R32 | Q01/Q03/Q06/Q09 |
| Guest and image | R13, R19, R22, R27, R31 | Q05/Q07/Q08 |
| Lifecycle and adoption | R11, R14–R19, R25, R29 | Q02/Q04/Q05/Q09 |
| Mobility | R13–R17, R22–R28 | Q07/Q08, with Q04 safety prerequisites |
| Shared services | R08, R13, R17, R21, R30 | Q05/Q07/Q09 |
| Resilience and operations | R08, R15–R17, R28–R30, R34–R35 | Q04/Q09/Q10 |
| Assurance and sovereignty | R03–R04, R13–R14, R25, R31–R32, R35 | Q01/Q03/Q06/Q09/Q10 |

Coverage includes actual enabled features/entitlements and alternate integration constraints. Product-family names do not establish security equivalence, backend behavior, performance or ownership of API fields.

## 6. Future release support record

Assurance publishes a release-bound, machine-readable matrix when qualifying evidence exists. Each row requires:

- A stable support-record ID; product release/image/configuration revisions; operation; method; and direction.
- Exact protected source/target installed-tuple references, including API/backend/features/entitlements; source omitted only for operations that genuinely have none.
- Guest/image, data/consistency, network/security/service, topology/failure and assurance profile versions.
- Required R-series obligations, campaign/gate references, evidence digests, independent review, limitations and acceptance scope.
- Validity period, expiry/revocation/retest triggers, dependent records and authorized publication level.

Publish separate fields for implemented behavior, verification, native qualification and operational acceptance by reading their authorities. A single green check or a vendor-wide "supported" field is prohibited because it conceals missing dimensions. Discovery availability, placement eligibility, qualification and plan-specific permission are different views.

Material adapter, platform/API/backend, guest, enforcement, transfer method or recovery changes require impact review. Reuse is limited to demonstrably unaffected evidence with an explicit scope decision. Failed, expired or revoked qualification removes operational eligibility immediately through the authoritative assurance/admission path; documentation edits alone are not an enforcement mechanism.
