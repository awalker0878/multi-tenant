# Appendix G — Glossary

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.

<a id="source-table-431"></a>

| Term | Definition |
| --- | --- |
| Assurance Profile | Defines required strength of isolation, dedicated/shared realization, inspection, evidence and testing. |
| Capability Registry | Machine-readable declaration of platform features that have been validated for placement. |
| Exposure | Approved connectivity between a WSD and a public, enterprise, partner or other external domain. |
| Flow Intention | Portable declaration of required communication between identities/services. |
| Management Zone (MZ) | Dedicated administration environment separated from business service activity. |
| Out-of-Band (OOB) | Management path using dedicated or otherwise separated management connectivity/interfaces. |
| PAZ | Public Access Zone mediating public/external access to internal resources. |
| OZ | Operations Zone for routine operational systems under the applicable control profile. |
| RZ | Restricted Zone for concentrations of sensitive/critical systems and data. |
| HRZ | Highly Restricted Zone for higher-assurance requirements. |
| Route Authority | Control-plane function that compiles routing from authorized intent rather than accepting arbitrary consumer routes. |
| Security Domain Instance | Isolated routing/policy namespace associated with a zone class, authority scope, platform/site and assurance profile. |
| Service Binding | Explicit consumer relationship to an approved provider service endpoint. |
| Tenant Namespace | Administrative ownership/RBAC/quota boundary; not automatically a security zone. |
| WSD | Workload Security Domain; the primary workload lifecycle and security-intent object. |
| ZIP | Zone Interface Point; security boundary system between two zones that enforces inter-zone policy. |

[Previous chapter](66-appendix-f-architecture-decision-record-template.md) · [Chapter index](README.md) · [Next chapter](68-appendix-h-normative-requirement-catalogue.md)
