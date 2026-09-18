# Document Control

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.

<a id="source-table-7"></a>

| Field | Value |
| --- | --- |
| Document title | Portable Multi-Tenant Secure Hosting Handbook |
| Version | Draft v1.0 |
| Status | Reference architecture and implementation blueprint |
| Audience | Enterprise architects, network/security architects, platform engineers, automation engineers, operations, security assessors, service owners |
| Primary purpose | Define a portable, secure-by-default multi-tenant hosting model and the controls required to implement it consistently across multiple platforms. |
| Normative vocabulary | SHALL = mandatory; SHOULD = recommended unless justified otherwise; MAY = optional. |
| Scope | Network and security architecture, platform realization, zero-touch provisioning, Terraform patterns, assurance, operations, governance, and lifecycle. |
| Out of scope | Application-specific architecture, product selection, firewall vendor selection, detailed site cabling, and platform licensing. |


<a id="source-table-8"></a>

| DESIGN INTENT<br>This handbook deliberately avoids inherited environment-specific naming, department names, existing VRF taxonomies, and legacy topology assumptions. It is a clean reference architecture derived from security boundaries, operational scale, portability, and automation requirements. |
| --- |

## Revision History


<a id="source-table-10"></a>

| Version | Date | Summary |
| --- | --- | --- |
| 1.0 | September 2026 | Initial complete handbook derived from the greenfield reference design. |

## Source and Standards Baseline

The handbook is architecture guidance. It is not a substitute for system categorization, a threat and risk assessment, the Information System Security Implementation Process (ISSIP), formal authorization, or product-specific security guidance. Requirements in this handbook should be tailored to the information system and documented when they differ from the baseline.

- Canadian Centre for Cyber Security ITSP.80.022 — Baseline Security Requirements for Network Security Zones, version 2.0.

- Canadian Centre for Cyber Security ITSG-33 — IT Security Risk Management: A Lifecycle Approach and its ISSIP annexes.

- Government of Canada Security Control Profile for cloud-based services at Protected B / Medium Integrity / Medium Availability (PBMM), where applicable.

- Current vendor and Terraform provider documentation for the implemented platforms. Provider capabilities change independently and must be validated at implementation time.

[Chapter index](README.md) · [Next chapter](02-executive-summary.md)
