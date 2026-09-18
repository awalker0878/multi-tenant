# 52. High availability and dependency failure behavior

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13399_1645000677"></a>
<a id="sec_52"></a>

A control-plane outage and a data-plane outage are different events. The system must not create a new permit path when a dependency is unavailable. Existing traffic continues only to the extent that the qualified implementation can preserve the required controls. A controller cannot guarantee continuity simply by declaring it. Test enforcement, session behavior and recovery against the actual versioned implementation.


<a id="source-table-703"></a>

| Failure | Expected controlled behavior |
| --- | --- |
| Catalogue/controller/runner unavailable | Existing qualified data plane continues where supported; new work queues safely; no substitute privileged manual automation |
| Admission/capability/approval unavailable | New or changed security-significant intent stops; no guessed defaults or stale blanket approval |
| IPAM/DNS unavailable | No new allocations or unsupported DNS changes; existing leases/records follow approved continuity; reconcile after recovery |
| Identity/PAM unavailable | No routine new privileged sessions; explicitly controlled break-glass route available and audited |
| KMS/PKI unavailable | No plaintext fallback or replacement key; document existing-key cache behavior and effect on restarts/new access |
| State backend unavailable | No untracked apply; recover backend/version and reconcile real resources before resuming |
| Central logging unavailable | Enforcement remains, buffering and loss alerts apply; mandatory profile safe-state rules evaluated |
| Edge/control node loss | Qualified HA/fencing and capacity preserve policy; no bypass link or permissive temporary route |
| Storage/site partition | Quorum/fencing prevents conflicting writers; choose recovery authority before promotion |
| Partial apply or API timeout | Journal the unknown outcome, query ownership/readiness and converge or compensate safely; do not duplicate resources |

Test asymmetrical partitions, not only a clean node shutdown. Confirm failure detection and fencing do not depend on the failed path, and that emergency access survives the failure it is meant to repair. Stateful security devices require explicit connection-state handling and return-path symmetry. Availability targets distinguish established-session survival, new-session success and recovery after enforcement returns.

<a id="req_FAIL_001"></a>

FAIL-001  Control-plane failure SHALL NOT create an implicit permit path.

Platform operations  \|  Verify: [CT-011](73-appendix-d-conformance-test-catalogue.md#test_CT_011), [CT-012](73-appendix-d-conformance-test-catalogue.md#test_CT_012), [CT-024](73-appendix-d-conformance-test-catalogue.md#test_CT_024), [CT-052](73-appendix-d-conformance-test-catalogue.md#test_CT_052)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_FAIL_002"></a>

FAIL-002  Failover and control-plane-loss scenarios SHALL be included in platform conformance testing.

Assurance engineering  \|  Verify: [CT-011](73-appendix-d-conformance-test-catalogue.md#test_CT_011), [CT-012](73-appendix-d-conformance-test-catalogue.md#test_CT_012), [CT-027](73-appendix-d-conformance-test-catalogue.md#test_CT_027), [CT-038](73-appendix-d-conformance-test-catalogue.md#test_CT_038), [CT-050](73-appendix-d-conformance-test-catalogue.md#test_CT_050), [CT-054](73-appendix-d-conformance-test-catalogue.md#test_CT_054), [CT-055](73-appendix-d-conformance-test-catalogue.md#test_CT_055)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_FAIL_003"></a>

FAIL-003  Every critical dependency SHALL have a qualified loss/partition/recovery behavior, including credential/key continuity, logging loss, state recovery and split-brain prevention; unavailable authority SHALL NOT authorize fallback bypass.

Platform operations  \|  Verify: [CT-027](73-appendix-d-conformance-test-catalogue.md#test_CT_027), [CT-038](73-appendix-d-conformance-test-catalogue.md#test_CT_038), [CT-044](73-appendix-d-conformance-test-catalogue.md#test_CT_044), [CT-050](73-appendix-d-conformance-test-catalogue.md#test_CT_050), [CT-054](73-appendix-d-conformance-test-catalogue.md#test_CT_054), [CT-055](73-appendix-d-conformance-test-catalogue.md#test_CT_055)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](51-capacity-performance-and-capacity-on-demand-operations.md) · [Chapter index](README.md) · [Next chapter](53-recovery-bootstrap-and-failback-runbooks.md)
