# 1. Operate service outcomes rather than isolated components

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Operations_Recovery_and_Transition_Playbook.docx) · [Chapter index](README.md)

> **Source:** OPS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d935614ed1639f56859dfe29bc226af4cfced35bafeb7d544440577ddaa95a09 -->
<!-- SOURCE-BLOCK OPS:17 BEGIN -->

<a id="OPS_01"></a>

<!-- SOURCE-BLOCK OPS:17 END -->

<!-- SOURCE-BLOCK OPS:18 BEGIN -->

The operator needs to know what the service promises, which controls make that promise valid and which team can repair each dependency.

<!-- SOURCE-BLOCK OPS:18 END -->

<!-- SOURCE-BLOCK OPS:19 BEGIN -->

Design basis and related records: [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [QUAL §7](../../assurance/site-qualification/7-operating-accountability-handover-and-change.md#QUAL_s_007)  •  [IK §9](../../implementation/delivery-guide/9-operational-handover-recovery-migration-and-retirement.md#IK_09)

<!-- SOURCE-BLOCK OPS:19 END -->

<!-- SOURCE-BLOCK OPS:20 BEGIN -->


<a id="source-table-20"></a>

| Operating question | Required current record | Decision when the record is missing |
| --- | --- | --- |
| Can new demand be accepted? | Service-class quota, actual commitments and all surviving capacity bottlenecks. | Queue, restrict or choose another already eligible placement; no borrowing security reserve. |
| Is the service still supported? | Installed versions, support horizon, vulnerabilities, exceptions and available recovery method. | Escalate and limit affected capability under the approved lifecycle policy. |
| Why does connectivity exist? | Domain authorities, approved operation, actual route and effective policy. | Investigate or restrict through the responsible authority; reachability is not permission. |
| Can this service be recovered? | Current copy/catalogue/key dependencies, useful restore evidence and accountable recovery owner. | Withdraw an unsupported promise or remediate; a completed backup job is insufficient. |
| Who accepts a change? | Scope owner, affected consumers, operating conditions and evidence dependencies. | Resolve authority before execution; a technical role name is not an assigned approver. |

<!-- SOURCE-BLOCK OPS:20 END -->

<!-- SOURCE-BLOCK OPS:21 BEGIN -->

<!-- SOURCE-BLOCK OPS:21 END -->

<!-- SOURCE-BLOCK OPS:22 BEGIN -->

Define an observation cadence and material-change triggers for each service parameter. This playbook does not invent organization-wide maintenance or incident deadlines. Use the actual service agreement to set response objectives, review intervals, support coverage and escalation contacts.

<!-- SOURCE-BLOCK OPS:22 END -->

<!-- SOURCE-BLOCK OPS:23 BEGIN -->

Monitoring spans data-path success, denied-path enforcement, controller health, storage/copy integrity, identity/key use, native task completion and capacity. Tenant-provided logs alone do not establish provider enforcement. Account for collection loss, clock quality and protected access to cross-tenant evidence.

<!-- SOURCE-BLOCK OPS:23 END -->

<!-- SOURCE-BLOCK OPS:24 BEGIN -->

Continue with: [OPS §2](2-specify-dependency-loss-before-it-becomes-an-incident.md#OPS_02)  •  [OPS §8](8-accept-operational-responsibility-for-the-delivered-scope.md#OPS_08)

<!-- SOURCE-BLOCK OPS:24 END -->

<!-- SOURCE-BLOCK OPS:25 BEGIN -->

<!-- SOURCE-BLOCK OPS:25 END -->

[Chapter index](README.md) · [Next chapter](2-specify-dependency-loss-before-it-becomes-an-incident.md)
