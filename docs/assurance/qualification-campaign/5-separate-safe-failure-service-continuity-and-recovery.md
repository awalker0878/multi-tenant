# 5. Separate safe failure, service continuity and recovery

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx) · [Chapter index](README.md)

> **Source:** QCP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 910b84a7b1772f27a456df31a09a96878a72e0f66c8f38cb7e5daaf79254007c -->
<a id="QCP_05"></a>

Authorize the fault scope, workload limit and restoration plan before using these cards. Do not perform intrusive tests against unrelated production tenants.

Design basis and related records: [NBD §7](../../engineering/network-boundaries/7-release-the-network-design-under-an-explicit-failure-model.md#NBD_07)  •  [QUAL §5](../site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)  •  [OPS §2](../../operations/recovery-transition/2-specify-dependency-loss-before-it-becomes-an-incident.md#OPS_02)


<a id="source-table-59"></a>

| Card / existing tests | Controlled observation | Independent result dimensions |
| --- | --- | --- |
| Q11-09: edge or link loss<br>CT-012, CT-024, CT-034 | Under approved representative load, observe the selected node/link failure and restoration using the site MOP. Capture new and established sessions. | Security: no bypass. Service: actual interruption and surviving load. Recovery: correct route/state after restoration. |
| Q11-10: dependency loss<br>CT-011, CT-027, CT-038, CT-050, CT-055 | Observe one scoped management, identity, key, logging or state dependency loss at a time; follow its accepted recovery procedure. | No fallback privilege/permit/plaintext. Existing and new operations match the documented limits. Evidence gaps and recovery time remain visible. |
| Q11-11: uncertain provisioning outcome<br>CT-045, CT-046, CT-048 | In a disposable scope, interrupt a response or executor at an approved point. Freeze competing writes; discover actual native tasks and resources before recovery. | No duplicate allocation or unsafe deletion. Denied unfinished resources remain owned. Retain task, plan, state and actual-outcome reconciliation. |
| Q11-12: isolated restore and cutover<br>CT-052, CT-053, CT-054, CT-060 | Restore a known disposable dataset and dependencies into the authorized recovery domain; validate consistency, identity/keys and paths before controlled activation. | Useful data and measured RTO/RPO; no ambiguous simultaneous writer; protection, return path and operating ownership survive cutover. |

An edge can preserve security by denying traffic while failing its availability target. A backup can produce readable files while failing the required consistency point. Report these outcomes separately; do not collapse them into one green status.

The safety envelope defines which failure is covered, who may stop the test, required surviving access, maximum permitted impact and restoration authority. A clean node shutdown does not represent every partition or overload; record the specific tested condition and any remaining untested scope.

Continue with: [OPS §4](../../operations/recovery-transition/4-recover-the-service-in-dependency-order.md#OPS_04)  •  [OPS §5](../../operations/recovery-transition/5-calculate-the-recovery-critical-path-and-data-point.md#OPS_05)  •  [IT §5](../../templates/implementation-mop/5-recovery-exercise-and-data-acceptance.md#IT_05)

[Previous chapter](4-observe-identity-storage-and-protocol-completeness.md) · [Chapter index](README.md) · [Next chapter](6-build-an-evidence-packet-a-reviewer-can-challenge.md)
