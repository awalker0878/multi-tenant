# 55. Incident response and scoped containment

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13405_1645000677"></a>
<a id="sec_55"></a>

Integrate the service with the adopting organization’s cyber-event process, including preparation, detection/assessment, mitigation/recovery and post-event improvement. GC CSEMP provides the relevant enterprise coordination context; this handbook does not replace reporting authorities or incident classifications. The incident commander and system owners define permitted actions and continuity priorities. \[[S12](77-appendix-h-primary-sources-and-implementation-references.md#S12)\]

Containment actions include quarantining a workload identity or instance, withdrawing public exposure, suspending egress, revoking a binding, raising ZIP security posture or pausing new placement on a suspect platform. The control plane records an IncidentOverride before ordinary reconciliation can restore the old desired state. Keep the narrowest effective scope and evaluate impacts on DNS/identity/logging/backup dependencies. A shared-domain quarantine may affect several WSDs and therefore requires explicit dependency analysis.


<a id="source-table-732"></a>

| Phase | Required operational record |
| --- | --- |
| Prepare | Runbooks, contact/authority roster, approved containment actions, test environment, log access, evidence custody and recovery material |
| Detect/assess | Observed indicators, affected tenants/domains, confidence, timeline, scope and immediate preservation decisions |
| Mitigate/recover | Approved override, before/after policy/routes, resource/credential actions, recovery validation and release authority |
| Post-event | Root-cause analysis, lessons, reconciled source, exception closure, test/profile changes and retained evidence |

Capture volatile configuration/route/policy facts when safe; urgent containment is not delayed solely to collect perfect evidence. Preserve who did what and why. Restrict forensic access to the authorized tenant/data scope and maintain artifact integrity. After recovery, revoke emergency grants, release containment through the proper authority, reconcile the source of truth and verify no stale route or credential persists.

<a id="req_IR_001"></a>

IR-001  Emergency containment SHALL be possible without requiring a physical-fabric redesign or broad outage to unrelated tenants.

Incident response  \|  Verify: [CT-057](73-appendix-d-conformance-test-catalogue.md#test_CT_057), [CT-067](73-appendix-d-conformance-test-catalogue.md#test_CT_067)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_IR_002"></a>

IR-002  Incident procedures SHALL define authority, scoped containment, evidence custody, coordination, recovery acceptance and reconciliation of emergency changes; containment release SHALL be explicit and attributable.

Incident response  \|  Verify: [CT-049](73-appendix-d-conformance-test-catalogue.md#test_CT_049), [CT-057](73-appendix-d-conformance-test-catalogue.md#test_CT_057), [CT-058](73-appendix-d-conformance-test-catalogue.md#test_CT_058), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S12](77-appendix-h-primary-sources-and-implementation-references.md#S12)  \|  new-v1.1

[Previous chapter](54-vulnerability-patch-and-support-lifecycle.md) · [Chapter index](README.md) · [Next chapter](56-lifecycle-retirement-and-secure-disposal.md)
