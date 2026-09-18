# 4. Observe identity, storage and protocol completeness

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx) · [Chapter index](README.md)

> **Source:** QCP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 910b84a7b1772f27a456df31a09a96878a72e0f66c8f38cb7e5daaf79254007c -->
<!-- SOURCE-BLOCK QCP:47 BEGIN -->

<a id="QCP_04"></a>

<!-- SOURCE-BLOCK QCP:47 END -->

<!-- SOURCE-BLOCK QCP:48 BEGIN -->

Test the actual native principal and data scope. A request made with administrator credentials is not evidence that a delegated tenant is restricted.

<!-- SOURCE-BLOCK QCP:48 END -->

<!-- SOURCE-BLOCK QCP:49 BEGIN -->

Design basis and related records: [PBS §7](../../engineering/platform-build/7-openstack-protect-mandatory-network-mutation.md#PBS_07)  •  [SVC §3](../../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md#SVC_s_003)  •  [SVC §4](../../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md#SVC_s_004)  •  [IK §5](../../implementation/delivery-guide/5-shared-security-services-and-protection.md#IK_05)

<!-- SOURCE-BLOCK QCP:49 END -->

<!-- SOURCE-BLOCK QCP:50 BEGIN -->


<a id="source-table-50"></a>

| Card / existing tests | Procedure and healthy control | Expected result / required artifact |
| --- | --- | --- |
| Q11-05: mandatory mutation authority<br>CT-019, CT-020, CT-022, CT-066 | With the actual tenant role, request forbidden baseline/group/port/external changes. Separately perform one approved workload operation. | Forbidden native mutations fail; entitled operation works. Record principal, target, operation and effective permission without storing secrets. |
| Q11-06: data attachment and copy scope<br>CT-037, CT-078 | Create disposable owned data and a known integrity marker. Test authorized access and bounded foreign attachment/clone/export attempts. | Owned access works; unauthorized data or lower-scope copy access fails. Retain data-service decisions, copy lineage and cleanup. |
| Q11-07: identity and key lifecycle<br>CT-028, CT-038, CT-079 | Use disposable credentials/key material in an approved scope. Observe valid use, rotation/revocation and denied foreign or revoked use. | Required use remains attributable; old authority expires as designed. Retain issuer/service logs and timestamps; no plaintext fallback. |
| Q11-08: service protocols and MTU<br>CT-008, CT-030, CT-031, CT-032 | Exercise DNS UDP/TCP and controlled fallback; check authorized resolver only. Test actual workload packet budget, PMTU and offered families end to end. | Necessary protocol behaviour works without broad egress or alternate-path bypass. Retain family/path matrix, packet budget and observed outcomes. |

<!-- SOURCE-BLOCK QCP:50 END -->

<!-- SOURCE-BLOCK QCP:51 BEGIN -->

<!-- SOURCE-BLOCK QCP:51 END -->

<!-- SOURCE-BLOCK QCP:52 BEGIN -->

For block storage, identify whether the operation is hypervisor-mediated or guest-initiated. Do not assume a guest firewall denied a virtual-disk attachment that never used the guest NIC. For keys, distinguish the actual host, storage service or workload client from the administrator who manages key lifecycle.

<!-- SOURCE-BLOCK QCP:52 END -->

<!-- SOURCE-BLOCK QCP:53 BEGIN -->

These observations elaborate the inherited test methods. Apply current source and approved site protocol profiles through engineering; do not infer that an “encrypted” flag proves endpoint identity, current cryptographic suitability or successful retained-data recovery.

<!-- SOURCE-BLOCK QCP:53 END -->

<!-- SOURCE-BLOCK QCP:54 BEGIN -->

Continue with: [OPS §4](../../operations/recovery-transition/4-recover-the-service-in-dependency-order.md#OPS_04)  •  [IT §4](../../templates/implementation-mop/4-test-procedure-and-actual-execution-record.md#IT_04)

<!-- SOURCE-BLOCK QCP:54 END -->

<!-- SOURCE-BLOCK QCP:55 BEGIN -->

<!-- SOURCE-BLOCK QCP:55 END -->

[Previous chapter](3-observe-network-paths-and-boundary-enforcement.md) · [Chapter index](README.md) · [Next chapter](5-separate-safe-failure-service-continuity-and-recovery.md)
