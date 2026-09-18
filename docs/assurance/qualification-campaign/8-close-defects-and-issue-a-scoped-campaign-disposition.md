# 8. Close defects and issue a scoped campaign disposition

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx) · [Chapter index](README.md)

> **Source:** QCP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 910b84a7b1772f27a456df31a09a96878a72e0f66c8f38cb7e5daaf79254007c -->
<!-- SOURCE-BLOCK QCP:85 BEGIN -->

<a id="QCP_08"></a>

<!-- SOURCE-BLOCK QCP:85 END -->

<!-- SOURCE-BLOCK QCP:86 BEGIN -->

Use an independent review where the adopted assurance model requires it. A test author’s expected outcome is not the final acceptance decision.

<!-- SOURCE-BLOCK QCP:86 END -->

<!-- SOURCE-BLOCK QCP:87 BEGIN -->

Design basis and related records: [DEL §3](../../governance/delivery-framework/3-apply-gate-dependencies-rather-than-numerical-order.md#DEL_03)  •  [IK §7](../../implementation/delivery-guide/7-tenant-provisioning-and-controlled-production-activation.md#IK_07)  •  [IT §4](../../templates/implementation-mop/4-test-procedure-and-actual-execution-record.md#IT_04)  •  [IT §7](../../templates/implementation-mop/7-gate-decision-and-production-activation.md#IT_07)

<!-- SOURCE-BLOCK QCP:87 END -->

<!-- SOURCE-BLOCK QCP:88 BEGIN -->


<a id="source-table-88"></a>

| Campaign decision | What must be recorded | Working response |
| --- | --- | --- |
| Scope and applicability | Exact offered service, tuple, topology, assertion set, families and approved exclusions. | \[Enter qcp campaign scope\] |
| Evidence result | Execution IDs, artifact references, observed results and freshness after changes. | \[Enter qcp evidence set\] |
| Defects / retests | Impact, owner, affected service, correction, targeted regression and retained original result. | \[Enter qcp defect disposition\] |
| Limits / residual work | Measured limits, untested conditions and capabilities not qualified. | \[Enter qcp remaining limits\] |
| Qualified scope | Actual technical review authority, decision reference, validity and review triggers. | \[Enter qcp qualification decision\] |
| Activation prerequisites | Required initial G4 evidence and separately valid service/security authority before G3. | \[Enter qcp activation dependencies\] |

<!-- SOURCE-BLOCK QCP:88 END -->

<!-- SOURCE-BLOCK QCP:89 BEGIN -->

<!-- SOURCE-BLOCK QCP:89 END -->

<!-- SOURCE-BLOCK QCP:90 BEGIN -->

A corrected defect is not closed until the changed assertion and its affected neighbours are observed again. An altered shared edge may invalidate more than the single failed case. A change in test scope or an approved not-applicable decision is recorded explicitly and cannot disguise a missing mandatory outcome.

<!-- SOURCE-BLOCK QCP:90 END -->

<!-- SOURCE-BLOCK QCP:91 BEGIN -->

The release disposition can be qualified for a narrow service, restricted with explicit exclusions, or blocked. Existing workloads follow their actual continuity/risk conditions; do not automatically destroy data because a new qualification is withheld. Initial operational/recovery readiness precedes production activation; recurring exercises after activation do not replace it.

<!-- SOURCE-BLOCK QCP:91 END -->

<!-- SOURCE-BLOCK QCP:92 BEGIN -->

Current release record: procedures and editable campaign fields supplied; all platform observations NOT RUN and all real qualification/activation decisions unissued.

<!-- SOURCE-BLOCK QCP:92 END -->

[Previous chapter](7-compare-vendor-realizations-without-assuming-migration.md) · [Chapter index](README.md)
