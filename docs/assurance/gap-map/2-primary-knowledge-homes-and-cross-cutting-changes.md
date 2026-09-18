# 2. Primary knowledge homes and cross-cutting changes

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/01_Gap_Map_and_Decision_Register_v1_4.docx) · [Chapter index](README.md)

> **Source:** GM — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 26dbaac8c13797b58ca5d057f76df8b3da63ec3f4b336036f18f5c6902512207 -->
<!-- SOURCE-BLOCK GM:31 BEGIN -->

<a id="__RefHeading___Toc1261_342027687"></a>
<a id="GM_s_002"></a>

<!-- SOURCE-BLOCK GM:31 END -->

<!-- SOURCE-BLOCK GM:32 BEGIN -->

Parent architecture: [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK GM:32 END -->

<!-- SOURCE-BLOCK GM:33 BEGIN -->


<a id="source-table-33"></a>

| Topic and parent chapters | Primary detail home | Change ripple to review |
| --- | --- | --- |
| Site/cells/failure · RA §§3–4, 14 | QUAL §2 | Eligible capacity, management recovery, co-residency and site service promises. |
| Fabric/routing/attachments · RA §§5, 8, 10 | NET §§1–5 | All vendor handoffs, address families, capacity and commissioning evidence. |
| Privileged access · RA §§6, 13 | NET §6 and SVC §3 | Executor permissions, incident/recovery access and shared-service administration. |
| Tenancy/native platforms · RA §§7, 15–18 | VND §§1–7 | Same fixture outcomes, sharing, operation coverage and qualified service classes. |
| Service/data/trust/recovery · RA §§9, 12–14, 27 | SVC §§1–6 | Bindings, copy/key lifetime, bootstrap dependency and activation/recovery. |
| Provisioning/change · RA §§20–25 | PROV §§1–6 | Authority, single writers, reservations, safe activation and brownfield lifecycle. |
| Capacity/operations/assurance · RA §§26, 28, 30 | QUAL §§3–7 | Actual service limits, assertions, ownership, evidence and operating conditions. |
| Exceptions and future services · RA §§19, 29 | QUAL §8 and GM §3 | Extension scope and explicit architecture/security adoption. |

<!-- SOURCE-BLOCK GM:33 END -->

<!-- SOURCE-BLOCK GM:34 BEGIN -->

<!-- SOURCE-BLOCK GM:34 END -->

<!-- SOURCE-BLOCK GM:35 BEGIN -->

Use the parent for the selected architectural decision, not as a dumping ground for every detailed table. Use the primary supplement for the detailed explanation, then point to it rather than duplicating it in several files. Vendor-specific mechanisms may differ while the named security/service outcome stays constant. A shared-service change must be reviewed across all vendor realizations that consume it.

<!-- SOURCE-BLOCK GM:35 END -->

<!-- SOURCE-BLOCK GM:36 BEGIN -->

Three kinds of completeness are tracked independently. Documentation coverage means the issue has a stated design, location and owner. Decision completion means the responsible authority has selected actual values and accepted the design. Qualification completion means observations on the actual implementation support the promised outcome. A gap can be documented here and still block production because the latter two have not occurred.

<!-- SOURCE-BLOCK GM:36 END -->

<!-- SOURCE-BLOCK GM:37 BEGIN -->


<a id="source-table-37"></a>

| Priority label | Meaning in this gap map | Not a claim of |
| --- | --- | --- |
| P0 | Resolve the decision or evidence before the affected foundational/security/service gate. | A confirmed critical vulnerability in a deployed environment. |
| P1 | Complete the engineering/operation detail before advertising or scaling the affected capability. | A universal urgency or remediation deadline. |
| P2 | Maintain document governance or qualify a deliberately excluded extension when it is offered. | Permission to ignore a requirement once the extension becomes in scope. |

<!-- SOURCE-BLOCK GM:37 END -->

<!-- SOURCE-BLOCK GM:38 BEGIN -->

<!-- SOURCE-BLOCK GM:38 END -->

<!-- SOURCE-BLOCK GM:39 BEGIN -->

Release maintenance includes link targets, source review status, requirement coverage, gate definitions, and representative scenario consistency. Preserve stable IDs when wording changes; record source and rationale. Stale site assumptions must not become reference architecture defaults. The registers support this process without mandating a new application or database.

<!-- SOURCE-BLOCK GM:39 END -->

[Previous chapter](1-document-family-scope-and-precedence.md) · [Chapter index](README.md) · [Next chapter](3-detailed-gap-register-and-treatment.md)
