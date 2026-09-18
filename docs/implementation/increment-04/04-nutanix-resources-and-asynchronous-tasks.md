# Nutanix resources and asynchronous tasks

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<a id="chapter_4"></a>

[Contents and release status](01-implementation-increment-04.md#chapter_1)

The selected networking/prism v4.3 profile observes a recorded task, the exact VPC/subnet resources, and the task again. It requires a stable completed task and matching selected resource values with exact accepted strong ETags. Task success alone cannot satisfy resource readback. \[U1–U5\]


<a id="source-table-45"></a>

| Object / signal | Checks implemented |
| --- | --- |
| VPC | extId, object type, native tenantId, name/type, external-subnet membership, externally routable prefixes and ETag |
| Subnet | extId, object type, native tenantId, name/type, VPC reference, external flag, IP configuration and ETag |
| Task binding | Exact opaque task ID, operation, time interval and affected resource IDs. IDs are encoded; callback URLs are not followed. |
| Task completeness | Zero subtasks and no batch summary; full exact affected-entity count/list. Limited or unresolved scope is unknown. |
| Completion | SUCCEEDED with valid completion time and no diagnostics needing review; later resource differences remain differences. |
| Failure and pending | QUEUED/RUNNING/CANCELING are pending. FAILED/CANCELED requires partial-effect review, not automatic rollback. |

## Missing metadata is not an empty or successful result

Some native fields can be omitted by an API representation. This strict profile does not silently treat an absent external-subnet list as empty or an absent status as success. Missing expected fields/ETag, weak ETag, foreign identity, incomplete entities or unknown states keep the outcome unresolved. An engineered site profile must establish safe normalization before relaxing these checks.

The task is deliberately limited to one known, fully enumerated operation. If its returned entity/subtask list is incomplete, the implementation does not recursively discover and cancel work. Preserve the native task identifier at submission; a missing identifier cannot be repaired by guessing a UUID.

## Installed capability is still separate

The wire profile is derived from the networking and prism Go SDK v4.3.1 interfaces and models. The new Python reader does not execute that SDK and does not negotiate another API. VMs, Flow policies, route resources, composite tasks and native repair are outside this increment. Native tenant identity, strong ETag behavior and actual read permissions must be accepted on the chosen platform. \[U1–U6\]

[Disabled Nutanix input example](../../../examples/nutanix_observation.json.example)

[Previous chapter](03-nsx-configuration-and-realization.md) · [Chapter index](README.md) · [Next chapter](05-interrupted-change-decision-procedure.md)
