# 5. Review sequence and change control

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/07_Quality/prior_v1_0/00_Delivery_Map.docx) · [Chapter index](README.md)

> **Source:** DEL10 — Delivery kits v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e332c1b37e63439169adf8b105573577fa1ea61bf32f6c3ba383dd69d83a788b -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="DEL_05"></a>

Use focused reviews at the point where a decision becomes expensive to reverse. Do not use document length or a green dashboard as the quality measure.

Baseline and related records: [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)  •  [RA §29](../../architecture/reference/29-architecture-decisions-and-alternatives.md#RA_s_029)  •  [QUAL §7](../../assurance/site-qualification/7-operating-accountability-handover-and-change.md#QUAL_s_007)


<a id="source-table-55"></a>

| Review | Questions to settle | Attendees / resulting record |
| --- | --- | --- |
| Architecture workshop | Scope, boundaries, sharing, service classes, alternative realizations and exit constraints. | Architecture, security, platform, network, storage and service owners; AK-01–08. |
| Engineering walkthrough | Trace one allowed and one denied path; lose one component; restore one dataset; adopt one existing resource. | Detailed-design owners and operators; EK-01–09 with discrepancies assigned. |
| Change rehearsal | Validate artifact identity, least privilege, one-writer ownership, safe stop, late tasks and recovery. | Implementers, change authority and assurance; reviewed MOP. |
| Qualification review | Assess actual assertion coverage, limits, negative controls and scoped evidence. | Independent reviewer where required; G2 disposition, not production permission. |
| Readiness / activation | Confirm support and required restore proof, operating authority and current tenant checks. | Service, operations, data/security authorities; initial G4 then G3. |
| Post-change / ongoing | Capture as-built differences, residual defects, measurement trends, expiry and renewed tests. | Operations and lifecycle owners; continuing G4 and change impact. |

If a requirement or topology changes, identify affected decisions, engineering schedules, modules/configurations, test cases, service promises and deployed environments. Record whether the change is a variation, a new service class or a revision to the adopted architecture. Retain the former baseline and actual historical decision.

[Previous chapter](4-working-records-examples-and-evidence.md) · [Chapter index](README.md) · [Next chapter](6-inputs-still-required-for-an-actual-deployment.md)
