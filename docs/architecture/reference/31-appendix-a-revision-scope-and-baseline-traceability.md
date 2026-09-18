# Appendix A — Revision scope and baseline traceability

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:419 BEGIN -->

<a id="__RefHeading___Toc3700_865363315"></a>
<a id="RA_app_A"></a>

<!-- SOURCE-BLOCK RA:419 END -->

<!-- SOURCE-BLOCK RA:420 BEGIN -->

The historical v1.2 revision basis was the 105-page v1.1 handbook and its companion catalogues. Draft v1.4 develops the architecture-led v1.2 document as its immediate baseline. \[[B1](34-appendix-d-sources-and-review-status.md#RA_src_B1); [B2](34-appendix-d-sources-and-review-status.md#RA_src_B2)\] The change is primarily architectural framing and engineering specificity: physical and logical components, selected native realizations, infrastructure interfaces and provisioning work packages now lead. Detailed API objects, controller status mechanics, schema definitions and code patterns are not part of the main architecture narrative.

<!-- SOURCE-BLOCK RA:420 END -->

<!-- SOURCE-BLOCK RA:421 BEGIN -->


<a id="source-table-421"></a>

| v1.1 material | v1.2 treatment |
| --- | --- |
| Foundations, tenant/domain/zone model | Retained and connected to physical topology and resource placement |
| Compute, storage, identity, keys, backup and recovery | Retained as hosting infrastructure; operational paths and dependency boundaries made explicit |
| Vendor implementation profiles | Expanded into deployment, routing/security and provisioning reference patterns |
| API/controller and Terraform internals | Translated to functional execution/ownership requirements; detailed code/schema design is supporting material |
| 194 requirements and 80 test procedures | Preserved in the accessible traceability package rather than embedded as the main architectural story |
| Historic source and migration records | Retained with explicit lineage; newly inspected references and access limitations identified |

<!-- SOURCE-BLOCK RA:421 END -->

<!-- SOURCE-BLOCK RA:422 BEGIN -->

<!-- SOURCE-BLOCK RA:422 END -->

<!-- SOURCE-BLOCK RA:423 BEGIN -->

## Explicit requirement clarifications

<!-- SOURCE-BLOCK RA:423 END -->

<!-- SOURCE-BLOCK RA:424 BEGIN -->

## API-003

<!-- SOURCE-BLOCK RA:424 END -->

<!-- SOURCE-BLOCK RA:425 BEGIN -->

Where a consumer-facing provisioning API is provided, it SHALL enforce immutable IDs, idempotent create, optimistic concurrency, typed/closed schemas, authorized references and authoritative service-owned status; stale or unauthorized updates SHALL fail before side effects. These controls MAY be implemented by an existing qualified service interface.

<!-- SOURCE-BLOCK RA:425 END -->

<!-- SOURCE-BLOCK RA:426 BEGIN -->

Scope clarification: preserves interface safety without requiring a new custom API/controller application. Existing qualified catalogue or service interfaces can implement the controls.

<!-- SOURCE-BLOCK RA:426 END -->

<!-- SOURCE-BLOCK RA:427 BEGIN -->

## TF-003

<!-- SOURCE-BLOCK RA:427 END -->

<!-- SOURCE-BLOCK RA:428 BEGIN -->

The provisioning workflow SHALL select the required hosting-platform and shared-service adapters before execution; adapters SHALL preserve their authority and lifecycle boundaries. A single giant conditional module SHOULD NOT attempt to implement all platforms.

<!-- SOURCE-BLOCK RA:428 END -->

<!-- SOURCE-BLOCK RA:429 BEGIN -->

Composite provisioning clarification: a chosen hosting stack is coordinated with independently owned security, address/name, data-protection and trust-service integrations.

<!-- SOURCE-BLOCK RA:429 END -->

<!-- SOURCE-BLOCK RA:430 BEGIN -->

All 194 requirement texts in the v1.2 catalogue remain unchanged in this v1.3 reference register. The two historical v1.2 clarifications above are retained, not newly revised. Every one of the 62 v1.1 chapters maps to one or more architecture chapters. The full requirement JSON and the linked CSV registers provide the full statements, owners, source identifiers, test links and original text. Moving a control into supporting material does not remove it. Requirements concerning interfaces can be implemented through existing qualified systems; no implicit authority is granted to weaken security because the main document is less code-centric.

<!-- SOURCE-BLOCK RA:430 END -->

<!-- SOURCE-BLOCK RA:431 BEGIN -->

The retained 80 verification procedures (including document/package and optional-interface checks) and 12 realization-specific addenda are explicitly not-run in the inherited execution records. New local document checks are reported separately and do not qualify infrastructure. Local integrity and publishing checks validate this document package only. Architecture decisions, actual platform qualification, service acceptance and formal authorization remain separate records. The companion audit register records documentation treatments, not live remediation claims.

<!-- SOURCE-BLOCK RA:431 END -->

<!-- SOURCE-BLOCK RA:432 BEGIN -->

Document relationship — Read the parent as the proposed infrastructure reference and provisioning strategy. Use the six linked supplements for engineering knowledge and open decisions, and the reference registers for retained normative statements and verification workload. The site low-level design still supplies actual physical values, product compatibility, executed integrations and evidence.

<!-- SOURCE-BLOCK RA:432 END -->

<!-- SOURCE-BLOCK RA:433 BEGIN -->

The legacy API/schema companion is not incorporated as a functioning implementation. Its earlier code-level audit findings are not closed by reorganizing the architecture. Any later adoption of that optional implementation requires its own corrected specification, testing and controlled compatibility decisions. GM explains documentation versus decision and qualification closure.

<!-- SOURCE-BLOCK RA:433 END -->

<!-- SOURCE-BLOCK RA:434 BEGIN -->

Related engineering: [Document family and precedence](../../assurance/gap-map/1-document-family-scope-and-precedence.md#GM_s_001)  •  [Current gap map](../../assurance/gap-map/3-detailed-gap-register-and-treatment.md#GM_s_003)

<!-- SOURCE-BLOCK RA:434 END -->

[Previous chapter](30-implementation-handoff-and-delivery-sequence.md) · [Chapter index](README.md) · [Next chapter](32-appendix-b-infrastructure-interface-schedule.md)
