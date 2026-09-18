# 7. Decisions, risk and review

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Architecture_Kit.docx) · [Chapter index](README.md)

> **Source:** AK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: f0cd99f187d5f883e0f752e07de20f8878bef02fa1d0b36817674ef59bfd9802 -->
<a id="AK_07"></a>

Use an architecture decision record for choices with material consequences. A decision records why an option is suitable for the offered scope, not merely that a product has a feature.

Baseline and related records: [RA §29](../reference/29-architecture-decisions-and-alternatives.md#RA_s_029)  •  [GM §4](../../assurance/gap-map/4-open-decision-package-for-implementation.md#GM_s_004)  •  [AT §6](../../templates/hld/6-architecture-decision-record.md#AT_06)


<a id="source-table-73"></a>

| Decision record | Minimum evidence |
| --- | --- |
| Problem and constraints | Business/service need, threat/failure assumptions, affected requirements and scope. |
| Viable alternatives | At least the realistic alternatives or a clear explanation of why no alternative meets the constraints. |
| Selected design | Components, boundary/authority model, integration interfaces and required capabilities. |
| Consequences | Security, availability, complexity, capacity/cost, operations, portability and exit limitations. |
| Authority and validity | Proposed/accepted/rejected status, actual decision owner, date, applicable scope and review triggers. |
| Follow-through | LLD schedule IDs, build ownership, qualification assertions, remaining blockers and superseded decisions. |

The risk register separates a design concern from an observed implementation defect. A proposed mitigating control remains proposed until implemented and evidenced. Risk acceptance records residual risk and conditions; it does not assert the missing control exists.

## Review challenge

Ask another discipline to identify the broadest route, most privileged credential, largest shared failure domain, weakest return-path assumption and hardest recovery dependency. Resolve the answer in the design and records rather than adding another generic assurance statement.

[Previous chapter](6-vendor-realization-and-provisioning-strategy.md) · [Chapter index](README.md) · [Next chapter](8-engineering-handoff-and-change-impact.md)
