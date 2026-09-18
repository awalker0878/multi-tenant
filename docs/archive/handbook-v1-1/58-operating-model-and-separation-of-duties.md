# 58. Operating model and separation of duties

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13413_1645000677"></a>
<a id="sec_58"></a>

Adopt a service-based operating model with accountable ownership of the durable contract, shared service products, foundation capacity, security policy and assurance. Tenant teams own workload requirements and application controls; provider teams own the qualified infrastructure and inherited controls. The precise split is recorded for each service rather than assumed from a platform brand or hosting location. \[[S05](77-appendix-h-primary-sources-and-implementation-references.md#S05); [S28](77-appendix-h-primary-sources-and-implementation-references.md#S28)\]


<a id="source-table-764"></a>

| Role | Accountability and authority boundary |
| --- | --- |
| Architecture authority | Portable model, requirements, approved design decisions and architectural change impact |
| Security authority / authorizing official | Categorization/profile decisions, risk acceptance, selected controls and formal authorization; technical testing may be delegated but decision authority is not fabricated |
| Foundation/network engineering | Physical fabric, attachments, underlay/EVPN, OOB and platform bootstrap within scoped identities |
| Platform/service engineering | Native adapters, compute/storage/identity/shared-service products, qualification and supported lifecycle |
| Security-edge operations | ZIP contexts, route/policy enforcement, sensor health, HA and edge capacity |
| Automation platform | API/controller, source/state/journal integrity, runners, profile registry and evidence service |
| Assurance / security operations | Test execution, independent review, event correlation, evidence freshness and incident coordination |
| Tenant service/data owner | Workload intent, application/data lifecycle, acceptance, retention, recovery requirements and declared extensions |

A requestor cannot approve their own high-risk privilege or exposure change merely because they operate the pipeline. Define who is responsible, accountable, consulted and informed for onboarding, profile changes, edge changes, emergency containment, risk acceptance, backup retention, restore and disposal. A single accountable role owns each decision, even when several teams execute it. Access reviews compare actual API/native roles with this model, not just job titles.

Operations handover includes ownership/contact escalation, service dependencies, SLO and recovery profiles, capacity, monitoring, credentials/break-glass, runbooks, known limitations, supported versions, costs and qualification evidence. No unresolved operational responsibility is silently assigned to a tenant at Service Ready.

<a id="req_OPS_001"></a>

OPS-001  Each service SHALL publish a provider/tenant/shared control responsibility matrix and accountable decision owners for its complete lifecycle, including inherited controls, support access and data disposal.

Service management  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062), [CT-079](73-appendix-d-conformance-test-catalogue.md#test_CT_079)  \|  Basis: [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05) / [S28](77-appendix-h-primary-sources-and-implementation-references.md#S28)  \|  new-v1.1

<a id="req_OPS_002"></a>

OPS-002  Production handover SHALL include owner/escalation, dependency, SLO/recovery, capacity, monitoring, runbook, support/version and evidence records; privileged access SHALL be reviewed against the actual authority model.

Service management  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](64-part-vii-governance-and-delivery.md) · [Chapter index](README.md) · [Next chapter](59-change-exceptions-and-risk-decisions.md)
