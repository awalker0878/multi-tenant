# Appendix F — Proposed local engineering parameters

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13441_1645000677"></a>
<a id="app_F"></a>

<a id="__RefHeading___Toc13443_1645000677"></a>

## Reference parameter set

These values are starting proposals for an implementation workshop. They are not government-mandated thresholds, approved cryptoperiods, purchased capacity commitments or measurements of a deployed service. Each production profile needs an owner, authority approval, version, applicability and measured feasibility; higher-authority or system-specific obligations override these examples.


<a id="source-table-1542"></a>

| Parameter | Proposed example | Qualification / adoption rule |
| --- | --- | --- |
| Event forwarding latency | Target ≤60 seconds under normal operation | Measured end-to-end receipt; critical event classes identified separately |
| Security drift detection | Target ≤15 minutes for polled configuration; event-driven where supported | Do not claim unseen configuration has been inspected |
| Privileged-access review | Quarterly and on role/incident change | Actual native/API privileges included, not only identity group names |
| Critical configuration recovery exercise | At least every 180 days and after major changes | Restore bootstrap/state/keys/catalog; target environment isolated |
| Representative data restore exercise | At least every 90 days and after material backup changes | Application consistency and actual recovered data point recorded |
| Evidence freshness for unchanged routine deployments | 24 hours as a starting cap | Material changes invalidate affected evidence immediately |
| Exception review horizon | At most 90 days for routine architecture exceptions | Shorter for elevated risk; source obligations may not allow an exception |
| Image vulnerability review | At publication and before deployment admission | Approved intelligence and installed package versions considered |
| Critical exploitable vulnerability response | Immediate triage; local plan target within 24 hours | Remediation deadline set by the security authority and applicable direction, not this example |
| Capacity operating reserve | Start with a modeled 20% reserve after the covered failure | Recalculate from measured workload, rebuild, maintenance and forecast; not a universal safe percentage |
| Example service availability | 99.9% over a defined 30-day window | Example AvailabilityProfile only; exclusions and measurement defined before offering |
| Example recovery objectives | RTO 240 minutes; RPO 60 minutes | Example RecoveryProfile; measured acceptance includes dependencies and service validation |
| Example backup retention / evidence retention | 30 days backup; 365 days evidence | Data-owner retention/hold and applicable obligations override examples |
| Example key rotation review | 365-day maximum planned interval as a design placeholder | Actual key type, cryptoperiod and current crypto policy determine the approved value |

### Profile adoption record

Record profile ID/version; offered service class; information envelope; proposed and approved parameters; rationale; measurement method; exact target implementation; evidence; capacity cost; operator owner; approving authority; effective/review dates; exceptions and migration consequences. A numeric default is not “approved” just because it exists in a schema example.

[Previous chapter](74-appendix-e-source-control-traceability-and-responsibility.md) · [Chapter index](README.md) · [Next chapter](76-appendix-g-operational-records-and-decision-templates.md)
