# Evidence inventory and external checks

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Handbook locations in findings refer to the delivered 105-page v1.1 edition. Companion paths are relative to Portable\_Secure\_Hosting\_v1\_1\_Companion/. Probe IDs M01-M25 resolve to the independent script and JSON observations in the audit evidence package. Original files were not modified.


<a id="source-table-206"></a>

| Audit artifact | Purpose |
| --- | --- |
| findings.json | 24 prioritized observations, recommendations, owners and closure tests. |
| chapter-coverage.json | Review disposition for all 62 chapters. |
| independent\_contract\_audit.py / independent-contract-audit.json | Reproducible 25-probe local audit and observed decisions. |
| rerun-validation.json | Fresh execution of the supplied 50-check suite. |
| artifact-verification.json / manifest-check.json | Actual input hashes, content/identity checks and all 39 listed package hashes. |
| independent-a11y.json | Fresh automated DOCX accessibility scan; not formal certification. |
| external-sources.json | Primary-source research used in this audit; reviewed 16 September 2026. |

## Primary-source checks

[W01 — Cyber Centre: ITSP.10.033 foreword, overview and introduction](https://www.cyber.gc.ca/en/guidance/cyber-security-privacy-risk-management/itsp10033/foreword-overview-introduction)

Confirms 31 March 2026 effective date, supersession of ITSG-33 Annex 3A, and related lifecycle-publication names.

[W02 — Cyber Centre: ITSP.40.111 cryptographic algorithms, version 5](https://www.cyber.gc.ca/en/guidance/cryptographic-algorithms-unclassified-protected-protected-b-information-itsp40111)

Confirms version 5 effective 29 May 2026.

[W03 — IETF RFC 7766: DNS Transport over TCP - Implementation Requirements](https://www.rfc-editor.org/rfc/rfc7766)

Sections 1 and 5 establish TCP transport support and explain the operational consequence of blocking it.

[W04 — Cyber Centre: ITSP.10.033 controls and assurance activities families](https://www.cyber.gc.ca/en/guidance/cyber-security-privacy-risk-management/itsp10033/controls-assurance-activities-families)

Authoritative control-family vocabulary used for proposed applicability/inheritance review.

[W05 — Cyber Centre: ITSP.40.062 secure protocol configuration](https://www.cyber.gc.ca/en/guidance/guidance-securely-configuring-network-protocols-itsp40062)

Protocol-configuration companion for cryptographic-profile work; version 3 effective January 2025.

The audit confirmed the handbook’s 2026 catalogue and cryptographic updates rather than assuming older references remained current. References to related lifecycle publications are not treated as proof that all of those documents are published, adopted, or supersede unspecified annexes. Organizational applicability, control selection and formal authorization remain decisions for the designated authorities.

[Previous chapter](26-f24-define-completion-independently-for-each-delivered-layer.md) · [Chapter index](README.md)
