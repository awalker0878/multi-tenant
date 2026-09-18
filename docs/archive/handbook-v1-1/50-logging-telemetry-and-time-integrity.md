# 50. Logging, telemetry and time integrity

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13395_1645000677"></a>
<a id="sec_50"></a>

Collect security-edge allow/deny decisions, distributed policy events, privileged actions, workload/platform identity events, route/IPAM/DNS changes, exposure changes, storage/copy operations, KMS access, backup administration, runner activity and configuration drift. Correlate them using stable tenant, WSD, domain, instance, object, operation and policy identifiers. Do not assume tenant-supplied logs are sufficient evidence for provider enforcement. GC Event Logging Guidance provides the organizational logging context; implement the applicable centralized collection and protection requirements. \[[S11](77-appendix-h-primary-sources-and-implementation-references.md#S11)\]


<a id="source-table-681"></a>

| Record area | Required semantic content |
| --- | --- |
| Who and where | Actor or workload identity; tenant/WSD/domain; source/destination or target resource; management/data plane; site/platform |
| What and why | Action, decision/outcome, policy/rule and version, operation/change/incident ID, authorization or exception reference |
| When and quality | UTC event and receipt time, clock source/offset health, sequence or correlation ID, collection status |
| Protection | Classification, redaction policy, access scope, integrity protection, retention class and deletion/hold state |

Avoid logging secrets, full credentials, unnecessary payloads or personal information merely to maximize collection. Define authorized access and minimization for cross-tenant queries. Synchronize infrastructure clocks to approved time services and alert on loss or excessive offset; preserve event receipt time so an unreliable source clock does not silently distort chronology. Include time services and logging in bootstrap/recovery design.

Define per-profile forwarding latency, local buffer capacity, retry/backoff, loss indicators, retention and overload behavior. Loss of central logging does not create a network permit path. Continue enforcement, buffer where supported, alert and restrict new security-significant changes as the approved profile dictates. If a mandatory high-assurance logging obligation cannot be sustained, follow the documented safe-state/continuity decision rather than either silently discarding evidence or blindly shutting down all tenants.

<a id="req_OBS_001"></a>

OBS-001  Logs SHALL contain stable identifiers sufficient to correlate tenant, WSD, Security Domain, policy, and deployment evidence.

Security operations  \|  Verify: [CT-010](73-appendix-d-conformance-test-catalogue.md#test_CT_010), [CT-049](73-appendix-d-conformance-test-catalogue.md#test_CT_049)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_OBS_002"></a>

OBS-002  Security control logging SHALL not depend solely on the tenant workload being healthy or cooperative.

Security operations  \|  Verify: [CT-010](73-appendix-d-conformance-test-catalogue.md#test_CT_010), [CT-050](73-appendix-d-conformance-test-catalogue.md#test_CT_050)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_OBS_003"></a>

OBS-003  Logging profiles SHALL define event coverage, attribution, time integrity, minimization, forwarding latency, buffering, loss alerting, retention, access and safe behavior during collection failure.

Security operations  \|  Verify: [CT-010](73-appendix-d-conformance-test-catalogue.md#test_CT_010), [CT-050](73-appendix-d-conformance-test-catalogue.md#test_CT_050), [CT-068](73-appendix-d-conformance-test-catalogue.md#test_CT_068)  \|  Basis: [S11](77-appendix-h-primary-sources-and-implementation-references.md#S11)  \|  new-v1.1

[Previous chapter](49-evidence-controls-and-authorization-records.md) · [Chapter index](README.md) · [Next chapter](51-capacity-performance-and-capacity-on-demand-operations.md)
