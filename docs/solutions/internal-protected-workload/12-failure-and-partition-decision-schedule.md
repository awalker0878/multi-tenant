# 12. Failure and partition decision schedule

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<a id="WD14_S12"></a>

Availability and security are separate observations. A denied flow during a fault is not evidence that the offered availability target was met. Conversely, continued traffic is not acceptable if it survived by bypassing the required security boundary. Record both outcomes, including the accepted interval for established sessions and new connections.

Test only under an approved scope with restoration procedures and protection for unrelated tenants. This document supplies expected behavior and evidence targets; it does not perform fault injection or claim observed results.

For every failure scenario, identify the failed components and the dependencies assumed to survive. A recovery path that depends on the failed management, identity or key service has not survived merely because a backup file is located on a different disk. A network partition requires writer ownership and fencing decisions, not just a lost-host alarm.


<a id="source-table-129"></a>

| Failure / change | Required controlled behavior | Evidence and decision owner |
| --- | --- | --- |
| One EC or SE member fails | Use only a qualified enforcing survivor; otherwise affected traffic denies. | Edge owner records forward/reply context, session outcome, load and measured interruption. |
| Service return route is missing or wrong | Do not add an unrestricted default to mask asymmetry; keep affected service unavailable. | Service/network owner compares intended prefix-to-SE route with observed replies. |
| Provider resolver or repository unavailable | No arbitrary external resolver, image or broad egress fallback. | Service owner assesses actual cached operation and pauses dependent builds. |
| KMS unavailable | No plaintext or unrelated replacement-key fallback; native existing/new access behavior is explicit. | Key/platform owners observe running I/O, new attachment/boot and recovery separately. |
| Platform manager or executor lost | No untracked changes; discover outstanding native tasks and current enforcement. | Platform owner confirms actual resource ownership before resuming or transferring writers. |
| Storage or inter-site partition | Do not promote an independent writable copy while authority is ambiguous. | Data/continuity owners establish fencing, consistency point and approved promotion. |
| Policy revoked during a live session | Deny new sessions; terminate or drain existing sessions within the approved bound. | Edge/service owners retain policy and session timestamps and resulting probes. |
| A tenant retires while backups remain held | Remove live reachability and grants; preserve authorized retained-data and key custody. | Data/protection owners account for every retained copy, disposition and required recovery access. |

Related documents: [SVC — Recovery and failback](../../architecture/shared-services/README.md#V14_SVC_START)  \|  [PROV — Interrupted operations](../../implementation/provisioning-strategy/README.md#V14_PROV_START)  \|  [QUAL — Observed acceptance](../../assurance/site-qualification/README.md#V14_QUAL_START)

[Previous chapter](11-test-resource-capacity-and-mtu-accounting.md) · [Chapter index](README.md) · [Next chapter](13-verification-assertions-and-actual-evidence.md)
