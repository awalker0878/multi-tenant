# Interrupted-change decision procedure

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<!-- SOURCE-BLOCK IMP04:53 BEGIN -->

<a id="chapter_5"></a>

<!-- SOURCE-BLOCK IMP04:53 END -->

<!-- SOURCE-BLOCK IMP04:54 BEGIN -->

[Contents and release status](01-implementation-increment-04.md#chapter_1)

<!-- SOURCE-BLOCK IMP04:54 END -->

<!-- SOURCE-BLOCK IMP04:55 BEGIN -->

An interrupted run first needs actual writer control and preserved data. A stopped runner does not prove that asynchronous native work stopped. Do not replay a create, cancel a task, unlock state, import a resource or restore an old state file merely because the original reply was lost.

<!-- SOURCE-BLOCK IMP04:55 END -->

<!-- SOURCE-BLOCK IMP04:56 BEGIN -->


<a id="source-table-56"></a>

| Condition | Reviewer outcome / required owner action |
| --- | --- |
| Active or unknown containment | KEEP\_INCIDENT\_CONTAINMENT / HOLD\_CONTAINMENT\_UNKNOWN; ordinary convergence cannot release it |
| Runner or writer not controlled | HOLD\_WRITER\_NOT\_FENCED; obtain actual scoped, current fencing evidence |
| New generation supersedes the attempt | HOLD\_SUPERSEDED\_CHANGE; compare against the current accepted change |
| Quarantine not independently verified | HOLD\_QUARANTINE\_NOT\_VERIFIED; matching config is not safe connectivity |
| Native task/publication pending | WAIT\_FOR\_NATIVE\_TASK; keep the original operation identity and do not resend |
| Task failed/canceled or config differs | INSPECT\_PARTIAL\_FAILURE / RECONCILE\_DIVERGENCE; assess actual resources and data |
| Missing/stale/contradictory observation | HOLD\_NATIVE\_UNCERTAINTY / HOLD\_INVALID\_EVIDENCE; resolve or recollect |
| All implemented record checks pass | READY\_FOR\_OPERATOR\_RECOVERY\_REVIEW; still no apply, delete or activation permission |

<!-- SOURCE-BLOCK IMP04:56 END -->

<!-- SOURCE-BLOCK IMP04:57 BEGIN -->

## Three independently controlled inputs

<!-- SOURCE-BLOCK IMP04:57 END -->

<!-- SOURCE-BLOCK IMP04:58 BEGIN -->

The offline reviewer binds the accepted manifest, readback report and change/recovery context. It checks target/scope/operation, digests, history consistency, freshness, generation and the recorded fence/quarantine/containment state. It recomputes the result instead of trusting a final label. The default freshness cap of 300 seconds is a local tool value, not government policy.

<!-- SOURCE-BLOCK IMP04:58 END -->

<!-- SOURCE-BLOCK IMP04:59 BEGIN -->

Every result retains may\_apply=false, may\_delete=false and may\_activate=false. The tool does not authenticate approval signatures or prove that a real writer was fenced. Evidence references and JSON hashes provide record linkage, not native control. Actual fencing, resource/data ownership and the next mutation decision remain with their authorities.

<!-- SOURCE-BLOCK IMP04:59 END -->

<!-- SOURCE-BLOCK IMP04:60 BEGIN -->

[Complete interrupted-change procedure](../../INTERRUPTED_CHANGE_RECOVERY.md)

<!-- SOURCE-BLOCK IMP04:60 END -->

<!-- SOURCE-BLOCK IMP04:61 BEGIN -->

[Deliberately incomplete recovery context example](../../../examples/recovery_context.json.example)

<!-- SOURCE-BLOCK IMP04:61 END -->

<!-- SOURCE-BLOCK IMP04:62 BEGIN -->

<!-- SOURCE-BLOCK IMP04:62 END -->

[Previous chapter](04-nutanix-resources-and-asynchronous-tasks.md) · [Chapter index](README.md) · [Next chapter](06-transport-credentials-and-protected-evidence.md)
