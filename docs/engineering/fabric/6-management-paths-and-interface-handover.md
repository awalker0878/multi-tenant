# 6. Management paths and interface handover

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/02_Fabric_Security_and_Interfaces_v1_4.docx) · [Chapter index](README.md)

> **Source:** NET — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9c557d7d94dbdf24630994d2676aca3ddfa80e67c2910fb1a29ea4561c591dcf -->
<!-- SOURCE-BLOCK NET:74 BEGIN -->

<a id="__RefHeading___Toc5755_1525915568"></a>
<a id="NET_s_006"></a>

<!-- SOURCE-BLOCK NET:74 END -->

<!-- SOURCE-BLOCK NET:75 BEGIN -->

Parent architecture: [RA §6](../../architecture/reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §20](../../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md#RA_s_020)

<!-- SOURCE-BLOCK NET:75 END -->

<!-- SOURCE-BLOCK NET:76 BEGIN -->

Publish an administrative path for each infrastructure role, not a single rule permitting an entire management network. Human operators use an authorized privileged endpoint and access boundary. Automated executors reach only their required management APIs. Support access is separate, bounded and attributable. Guest administration terminates on assigned workload interfaces and does not borrow hypervisor credentials.

<!-- SOURCE-BLOCK NET:76 END -->

<!-- SOURCE-BLOCK NET:77 BEGIN -->


<a id="source-table-77"></a>

| Actor | Permitted target | Prohibited expansion / recovery concern |
| --- | --- | --- |
| Fabric operator/executor | Approved switch and OOB management interfaces. | No workload/service administrator rights implied; preserve console access for fabric failure. |
| Platform operator/executor | Selected Prism, vCenter/NSX or OpenStack administration within scope. | No unrestricted security-edge, identity-root or other tenant authority. |
| Edge operator/executor | Boundary contexts and policy under security approval. | No tenant guest credentials; no use of data-path ZIP as management transit. |
| Backup operator | Capture/protection administration under assigned authority. | Protected-copy destruction is a separate decision; API orchestration and data transfer are distinct. |
| Guest operator | Approved tenant guest access service. | No BMC, host, array or provider management visibility by implication. |
| Emergency custodian | Explicit minimum recovery targets for the declared failure. | No anonymous shared access; offline records, expiry/revocation and post-use reconciliation. |

<!-- SOURCE-BLOCK NET:77 END -->

<!-- SOURCE-BLOCK NET:78 BEGIN -->

<!-- SOURCE-BLOCK NET:78 END -->

<!-- SOURCE-BLOCK NET:79 BEGIN -->

An interface handover for IF-01 through IF-12 records the exact endpoint membership, transport layer, initiating party, routing owner, enforcement point, authentication, address families, required performance, dependencies, failure action and retirement conditions. The parent Appendix B remains the authoritative interface-class list. This supplement supplies the engineering method; the site design supplies actual values. Interface owners jointly resolve conflicts before a dependent package activates traffic.

<!-- SOURCE-BLOCK NET:79 END -->

<!-- SOURCE-BLOCK NET:80 BEGIN -->


<a id="source-table-80"></a>

| Interface family | Detailed design home | Handover consumer |
| --- | --- | --- |
| IF-01/02 · underlay and platform transport | NET §§1, 5; actual route and MTU schedule. | P2 platform commissioning. |
| IF-03/04 · domain attachment and ZIP | NET §§2–3; paired authorities and path evidence. | P4/P5 domain and workload delivery. |
| IF-05/06 · management and OOB | NET §6; SVC §3; actual privileged/recovery scope. | Every privileged work package. |
| IF-07/08 · platform data and service consumption | SVC §§1–5; actual storage/service identities. | P2/P3 foundations and P5 service activation. |
| IF-09 · provisioning handoff | PROV §1; ownership and accepted dependencies. | The next authorized work package. |
| IF-10/11/12 · inter-site, external and evidence | SVC §6; NET §3; QUAL §§5–7. | Recovery, exposure and operational acceptance. |

<!-- SOURCE-BLOCK NET:80 END -->

<!-- SOURCE-BLOCK NET:81 BEGIN -->

<!-- SOURCE-BLOCK NET:81 END -->

<!-- SOURCE-BLOCK NET:82 BEGIN -->

Related engineering: [Parent infrastructure interface schedule](../../architecture/reference/32-appendix-b-infrastructure-interface-schedule.md#RA_app_B)  •  [Site design records](../../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)

<!-- SOURCE-BLOCK NET:82 END -->

[Previous chapter](5-mtu-performance-and-failure-engineering.md) · [Chapter index](README.md) · [Next chapter](07-references-parent-basis-and-external-context.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0009 — Separate management security, platform control and OOB recovery](../../adr/0009-separate-management-security-platform-control-and-oob-recovery.md)

<!-- END GENERATED DECISION LINKS -->
