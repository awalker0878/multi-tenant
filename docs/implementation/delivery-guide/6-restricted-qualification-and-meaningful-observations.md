# 6. Restricted qualification and meaningful observations

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Implementation_Kit.docx) · [Chapter index](README.md)

> **Source:** IK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b16b8843bfbafd1b417d611903f5b8038f4794efd4f22c995bee1cb36f9ebb41 -->
<!-- SOURCE-BLOCK IK:57 BEGIN -->

<a id="IK_06"></a>

<!-- SOURCE-BLOCK IK:57 END -->

<!-- SOURCE-BLOCK IK:58 BEGIN -->

Use RB-06 under an explicit non-production test authorization. Candidate capacity can host a restricted disposable fixture to obtain qualification evidence; that permission is not production acceptance.

<!-- SOURCE-BLOCK IK:58 END -->

<!-- SOURCE-BLOCK IK:59 BEGIN -->

Baseline and related records: [WD §11](../../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md#WD14_S11)  •  [WD §13](../../solutions/internal-protected-workload/13-verification-assertions-and-actual-evidence.md#WD14_S13)  •  [QUAL §5](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

<!-- SOURCE-BLOCK IK:59 END -->

<!-- SOURCE-BLOCK IK:60 BEGIN -->


<a id="source-table-60"></a>

| Campaign step | What to record | Evidence quality check |
| --- | --- | --- |
| Select scope | Service class, tuple, topology, sharing, families, changed features and requirement assertions. | Select applicable observations; do not make a second qualified stack a prerequisite to the first. |
| Authorize and prepare | Permitted fault/probe scope, disposable data, time window, restoration and stop authority. | Protect unrelated tenants; no intrusive or destructive test outside this scope. |
| Build fixture | Two tenants/four domains; approved services and one temporary sequential same-domain probe. | Peak guest fixture demand is accounted for separately from infrastructure overhead. |
| Prove control paths | Establish healthy endpoints and expected permitted functions before negative observations. | A timeout from a dead endpoint cannot establish a successful isolation result. |
| Observe outcomes | Capture intended versus realized path, native roles, policy, resource/copy ownership, fault and recovery result. | Distinguish security continuity, availability and actual recovery; no success inferred from tool exit alone. |
| Review and release | Record passed, failed, blocked, not-run or justified not-applicable; reviewer and immutable artifact references. | Unexecuted or missing mandatory evidence blocks the corresponding qualification. |

<!-- SOURCE-BLOCK IK:60 END -->

<!-- SOURCE-BLOCK IK:61 BEGIN -->

<!-- SOURCE-BLOCK IK:61 END -->

<!-- SOURCE-BLOCK IK:62 BEGIN -->

The kit carries 80 historical CT procedures, 12 realization addenda and 12 W14 assertions as reference material. They are not 104 executed tests. Applicability must be resolved for the target, and individual assertions may require several observations.

<!-- SOURCE-BLOCK IK:62 END -->

<!-- SOURCE-BLOCK IK:63 BEGIN -->

Use IT §4 for each test execution and IT §5 for recovery. Include the actual tuple, observation time, topology revision and target identity; never prefill an observed result from an expected result.

<!-- SOURCE-BLOCK IK:63 END -->

<!-- SOURCE-BLOCK IK:64 BEGIN -->

<!-- SOURCE-BLOCK IK:64 END -->

[Previous chapter](5-shared-security-services-and-protection.md) · [Chapter index](README.md) · [Next chapter](7-tenant-provisioning-and-controlled-production-activation.md)
