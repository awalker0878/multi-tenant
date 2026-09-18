# 6. Build an evidence packet a reviewer can challenge

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx) · [Chapter index](README.md)

> **Source:** QCP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 910b84a7b1772f27a456df31a09a96878a72e0f66c8f38cb7e5daaf79254007c -->
<a id="QCP_06"></a>

Evidence supports an assertion only when its target, scope, time and observation method match the claim.

Design basis and related records: [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)  •  [QUAL §5](../site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)  •  [IT §4](../../templates/implementation-mop/4-test-procedure-and-actual-execution-record.md#IT_04)


<a id="source-table-68"></a>

| Record area | Minimum content | Review rejection example |
| --- | --- | --- |
| Identity and scope | Case/assertion, actual tenant/domain/resource, topology and component/API/provider revision. | A passing result refers to yesterday’s gateway or another service class. |
| Preconditions | Healthy allowed controls, actual placement, required services, load and authorized test scope. | A timeout is labelled isolation success while the target service is stopped. |
| Observation | Actual requests/results, native policy/path decisions, timestamps and relevant dependency state. | Expected wording was copied into the observed-result field. |
| Artifact integrity | Protected artifact reference, collection time, integrity identifier, custodian and access scope. | A filename or signature-reference string is treated as verified authenticity. |
| Disposition | Passed, failed, blocked, not-run or approved not-applicable; reviewer, reasons and residual gaps. | Missing required evidence is reclassified as not-applicable merely to close a gate. |

## Worked review example

A cross-tenant connection times out, but the same-tenant positive control also fails. The correct disposition is blocked pending a healthy control, not passed. After the endpoint is restored, repeat both observations and retain the original blocked record. A subsequent passing test is a new result; it does not rewrite what happened earlier.

Evidence freshness follows material change as well as the approved interval. Recheck affected observations after routing, roles, group membership, backend, key custody or placement changes. Keep historical authorization separate from current technical status. A reviewer accepts the supported scope; software or a workbook does not issue risk authority.

Continue with: [QCP §8](8-close-defects-and-issue-a-scoped-campaign-disposition.md#QCP_08)  •  [OPS §8](../../operations/recovery-transition/8-accept-operational-responsibility-for-the-delivered-scope.md#OPS_08)

[Previous chapter](5-separate-safe-failure-service-continuity-and-recovery.md) · [Chapter index](README.md) · [Next chapter](7-compare-vendor-realizations-without-assuming-migration.md)
