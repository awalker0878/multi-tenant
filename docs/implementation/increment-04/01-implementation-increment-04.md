# Implementation Increment 04

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<a id="chapter_1"></a>

*Native readback and interrupted-change recovery*

17 September 2026 • Candidate native integrations • Executed local HTTPS and packet evidence

## Read the actual platform state before deciding how to recover

This increment implements exact-resource NSX and Nutanix readers and an offline recovery reviewer. The readers separate accepted configuration, current native status and task completion. The reviewer checks whether the observations and externally controlled recovery records belong to the same current change. Neither component mutates infrastructure or issues operating authorization.


<a id="source-table-5"></a>

| Delivered | Evidence boundary |
| --- | --- |
| NSX Local Manager object and intent-status reads | Selected configuration and enforcing-system status; not every host’s effective rules |
| Nutanix VPC/subnet and single-task reads | Networking/prism v4.3 candidate profile; no composite tasks or native changes |
| Interrupted-change triage and local HTTPS fault campaign | Actual local code/protocol tests; simulated fence/quarantine records |
| Ten existing Terraform module/root pairs retained | Engine/plugins still unavailable; native validation and qualification not run |

No user or vendor infrastructure was contacted. The toolchain download retry failed at container DNS resolution. Existing DNS and routed IPv4/mTLS tests were rerun separately; they do not qualify these native readers.

## Guide navigation

[2. Infrastructure ownership and readback coverage](02-infrastructure-ownership-and-readback-coverage.md#chapter_2)

[3. NSX configuration and realization](03-nsx-configuration-and-realization.md#chapter_3)

[4. Nutanix resources and asynchronous tasks](04-nutanix-resources-and-asynchronous-tasks.md#chapter_4)

[5. Interrupted-change decision procedure](05-interrupted-change-decision-procedure.md#chapter_5)

[6. Transport, credentials and protected evidence](06-transport-credentials-and-protected-evidence.md#chapter_6)

[7. Local execution and observed results](07-local-execution-and-observed-results.md#chapter_7)

[8. Native commissioning and stopping conditions](08-native-commissioning-and-stopping-conditions.md#chapter_8)

[9. Primary native-interface sources](09-primary-native-interface-sources.md#chapter_9)

[10. Release integrity and remaining work](10-release-integrity-and-remaining-work.md#chapter_10)

[Chapter index](README.md) · [Next chapter](02-infrastructure-ownership-and-readback-coverage.md)
