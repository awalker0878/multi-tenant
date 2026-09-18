# 2. Day-0 and steady-state commissioning without circular dependencies

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/04_Provisioning_and_Commissioning_v1_4.docx) · [Chapter index](README.md)

> **Source:** PROV — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 483df77cff70166fbdfdf711135efa3beeecc8fe1015a58290cbebff5b80bdfd -->
<!-- SOURCE-BLOCK PROV:34 BEGIN -->

<a id="__RefHeading___Toc7814_1525915568"></a>
<a id="PROV_s_002"></a>

<!-- SOURCE-BLOCK PROV:34 END -->

<!-- SOURCE-BLOCK PROV:35 BEGIN -->

Parent architecture: [RA §6](../../architecture/reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §21](../../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md#RA_s_021)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)

<!-- SOURCE-BLOCK PROV:35 END -->

<!-- SOURCE-BLOCK PROV:36 BEGIN -->

Day 0 creates the conditions that normal automation consumes. Start with a controlled console/OOB path, operator trust and verified artifacts. Identify the minimum name/time, identity or emergency identity, certificate trust, key access, configuration/state recovery and installation repositories needed while the new cell is unavailable. Their initial placement may be external to that cell, but it remains explicitly governed. \[[B2](07-references-parent-basis-and-external-context.md#PROV_src_B2) §21\]

<!-- SOURCE-BLOCK PROV:36 END -->

<!-- SOURCE-BLOCK PROV:37 BEGIN -->


<a id="source-table-37"></a>

| Commissioning stage | Infrastructure action | Exit and safe pause point |
| --- | --- | --- |
| Site preparation | Verify physical resource, fault-domain, port-role and support inventory; secure staging. | No default-access device is exposed outside the controlled commissioning path. |
| Independent administration | Establish approved console/OOB, scoped initial credentials and recovery custody. | The intended primary fabric/platform failure does not remove the only administration path. |
| Minimum dependencies | Provide trusted name/time, identity or approved emergency path, certificates, artifacts and required key access. | Their actual locations and dependency graph are known; no assumed service exists only inside the unbuilt platform. |
| Protected execution | Prepare scoped tooling and recoverable configuration/state records. | Artifact integrity and endpoint trust checked; credentials are not embedded in source. |
| Transport and platform installation | Commission P1, then supported P2 installation with required bootstrap dependencies. | Routing, MTU, management and platform baseline observed before tenant allocation. |
| Common services and joint testing | Commission P3 and complete representative P2/P3 integration/failure tests. | Service envelope accepted with actual capacity, dependencies and owners. |
| Transfer to steady state | Move temporary ownership/dependencies to agreed steady-state services and verify recovery again. | Temporary grants revoked without deleting the sole emergency or recovery material. |

<!-- SOURCE-BLOCK PROV:37 END -->

<!-- SOURCE-BLOCK PROV:38 BEGIN -->

<!-- SOURCE-BLOCK PROV:38 END -->

<!-- SOURCE-BLOCK PROV:39 BEGIN -->

Use a dependency-cut review: for every primary service, remove the resource or fault domain it is meant to recover from and ask whether the recovery plan still has an authorized path to the necessary keys, configuration and data. A backup on another datastore may still depend on the same failed identity provider or controller. Logical duplication does not demonstrate independence.

<!-- SOURCE-BLOCK PROV:39 END -->

<!-- SOURCE-BLOCK PROV:40 BEGIN -->

The transition record names each temporary endpoint, credential, route, artifact store and exception; its consuming package; its steady-state replacement; the verification performed after transfer; and the authority allowed to retire it. Bootstrap expiry must not automatically remove a still-required recovery dependency. Unresolved transitions remain an explicit operating restriction rather than hidden permanent defaults.

<!-- SOURCE-BLOCK PROV:40 END -->

<!-- SOURCE-BLOCK PROV:41 BEGIN -->

Subsequent capacity expansion reuses P1–P3 controls. Hosts, edge contexts, storage pools and attachment capacity enter service only after baseline, compatibility, surviving capacity and ownership checks. An expansion may be automated, but it remains a foundation operation with a different impact boundary from adding one workload.

<!-- SOURCE-BLOCK PROV:41 END -->

<!-- SOURCE-BLOCK PROV:42 BEGIN -->

Related engineering: [Trust-service recovery](../../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md#SVC_s_003)  •  [Recovery dependency order](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [Fault-domain record](../../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)

<!-- SOURCE-BLOCK PROV:42 END -->

[Previous chapter](1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [Chapter index](README.md) · [Next chapter](3-terraform-native-tools-and-operation-level-support.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0014 — Bootstrap management and trust before consuming native APIs](../../adr/0014-bootstrap-management-and-trust-before-consuming-native-apis.md)
- [ADR-0029 — Keep recovery trust material independent of the platform it unlocks](../../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md)

<!-- END GENERATED DECISION LINKS -->
