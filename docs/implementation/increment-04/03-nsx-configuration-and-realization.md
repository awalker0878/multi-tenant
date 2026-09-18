# NSX configuration and realization

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<!-- SOURCE-BLOCK IMP04:31 BEGIN -->

<a id="chapter_3"></a>

<!-- SOURCE-BLOCK IMP04:31 END -->

<!-- SOURCE-BLOCK IMP04:32 BEGIN -->

[Contents and release status](01-implementation-increment-04.md#chapter_1)

<!-- SOURCE-BLOCK IMP04:32 END -->

<!-- SOURCE-BLOCK IMP04:33 BEGIN -->

The selected Local Manager pattern reads the exact object, reads its intent status, and reads the object again. Configuration identity, selected values and \_revision must remain consistent around the status query. Two identical completed samples are required. A native write or status-refresh POST is never issued. \[N1–N4\]

<!-- SOURCE-BLOCK IMP04:33 END -->

<!-- SOURCE-BLOCK IMP04:34 BEGIN -->


<a id="source-table-34"></a>

| Observation | Required match / reason for a hold |
| --- | --- |
| Configuration identity | Exact path, id, resource type and nonnegative native revision; no similar-name substitution |
| Policy and rules | Category, sequence, statefulness; rule identity/order/action, direction/family, logging/enabled state, membership and negation, scope, referenced/inline services and profiles |
| Intent version | Separately recorded expected intent\_version. It is not assumed equal to the configuration \_revision. |
| Publication and aggregate status | Publication REALIZED and consolidated SUCCESS; pending/error/unknown remain distinct |
| Enforcing-system coverage | Exactly the accepted enforcement-point paths, each reporting SUCCESS; no missing, extra or duplicate span |
| Stable sampling | A config revision change around status collection is uncertain; do not combine two different revisions into one success |

<!-- SOURCE-BLOCK IMP04:34 END -->

<!-- SOURCE-BLOCK IMP04:35 BEGIN -->

## Rules are not normalized into apparent equivalence

<!-- SOURCE-BLOCK IMP04:35 END -->

<!-- SOURCE-BLOCK IMP04:36 BEGIN -->

The implementation preserves order and exact list membership. Expected rule sequences must be unique. Source/destination exclusion flags, inline services and profile lists are explicit; changed negation or extra service entries cannot be hidden behind an unchanged group/service name. Missing fields remain unknown rather than silently defaulted. \[N3\]

<!-- SOURCE-BLOCK IMP04:36 END -->

<!-- SOURCE-BLOCK IMP04:37 BEGIN -->

## What a matching status does not prove

<!-- SOURCE-BLOCK IMP04:37 END -->

<!-- SOURCE-BLOCK IMP04:38 BEGIN -->

The API’s enforcement-point status refers to an enforcing system/site, not proof that every ESXi or Edge node has the intended rules. This profile does not request each transport node’s enforced state, inspect the entire global rule hierarchy, resolve every group’s actual membership or run a native packet trace. Those remain separate qualification and operating observations. \[N1\]

<!-- SOURCE-BLOCK IMP04:38 END -->

<!-- SOURCE-BLOCK IMP04:39 BEGIN -->

Only the Local Manager /infra path profile is implemented. Global Manager and project-root variants are not translated automatically. The consulted latest documentation identifies NSX 9.1.1.0; this does not establish compatibility with an installed release or with the retained provider version. An unsupported status/resource combination remains a hold, not a fallback.

<!-- SOURCE-BLOCK IMP04:39 END -->

<!-- SOURCE-BLOCK IMP04:40 BEGIN -->

[Detailed native procedure and selected-field coverage](../../NATIVE_READBACK.md)

<!-- SOURCE-BLOCK IMP04:40 END -->

<!-- SOURCE-BLOCK IMP04:41 BEGIN -->

<!-- SOURCE-BLOCK IMP04:41 END -->

[Previous chapter](02-infrastructure-ownership-and-readback-coverage.md) · [Chapter index](README.md) · [Next chapter](04-nutanix-resources-and-asynchronous-tasks.md)
