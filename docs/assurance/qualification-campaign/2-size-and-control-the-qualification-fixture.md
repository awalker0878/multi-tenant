# 2. Size and control the qualification fixture

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx) · [Chapter index](README.md)

> **Source:** QCP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 910b84a7b1772f27a456df31a09a96878a72e0f66c8f38cb7e5daaf79254007c -->
<!-- SOURCE-BLOCK QCP:27 BEGIN -->

<a id="QCP_02"></a>

<!-- SOURCE-BLOCK QCP:27 END -->

<!-- SOURCE-BLOCK QCP:28 BEGIN -->

Four permanent endpoints provide one endpoint per domain. Additional controlled endpoints are required to test communication within a single domain.

<!-- SOURCE-BLOCK QCP:28 END -->

<!-- SOURCE-BLOCK QCP:29 BEGIN -->

Design basis and related records: [WD §2](../../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md#WD14_S02)  •  [WD §11](../../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md#WD14_S11)  •  [EK §6](../../engineering/delivery-guide/6-capacity-mtu-performance-and-failure-analysis.md#EK_06)  •  [IK §6](../../implementation/delivery-guide/6-restricted-qualification-and-meaningful-observations.md#IK_06)

<!-- SOURCE-BLOCK QCP:29 END -->

<!-- SOURCE-BLOCK QCP:30 BEGIN -->


<a id="source-table-30"></a>

| Fixture allocation | vCPU | Guest memory | Requested virtual disks |
| --- | --- | --- | --- |
| Four permanent endpoints | 8 | 16 GiB | 320 GiB |
| One sequential temporary probe | 2 | 4 GiB | 80 GiB |
| Sequential test peak | 10 | 20 GiB | 400 GiB |
| Alternative: four simultaneous probes | 8 additional | 16 GiB additional | 320 GiB additional |
| Simultaneous test peak | 16 | 32 GiB | 640 GiB |

<!-- SOURCE-BLOCK QCP:30 END -->

<!-- SOURCE-BLOCK QCP:31 BEGIN -->

<!-- SOURCE-BLOCK QCP:31 END -->

<!-- SOURCE-BLOCK QCP:32 BEGIN -->

The permanent and sequential peak totals are inherited from WD. The simultaneous alternative is a local calculation using the same 2-vCPU, 4-GiB, 80-GiB probe assumption for each domain. Neither case represents host sizing, physical storage consumption or a delivered service guarantee. Platform controllers, edges, service appliances, replicas, backups and failure reserve are additional.

<!-- SOURCE-BLOCK QCP:32 END -->

<!-- SOURCE-BLOCK QCP:33 BEGIN -->

For sequential testing, instantiate or reassign the probe only through the supported controlled lifecycle, one domain at a time. Before moving it, remove old credentials, identities, policy and data; verify no stale attachment remains. Never attach one unrestricted probe simultaneously to independent domains. Simultaneous testing needs separately scoped probes and its own capacity reservation.

<!-- SOURCE-BLOCK QCP:33 END -->

<!-- SOURCE-BLOCK QCP:34 BEGIN -->

Same-host coverage is applicable only where the adopted sharing and placement permit both test endpoints on that host. Cross-host coverage requires actual placement evidence, not an assumed scheduler choice. Record temporary resources in inventory and verify their cleanup after the campaign.

<!-- SOURCE-BLOCK QCP:34 END -->

<!-- SOURCE-BLOCK QCP:35 BEGIN -->

Healthy-control prerequisite: prove the actual source, destination service and permitted path work before interpreting a denied probe. A dead endpoint produces a blocked test, not isolation evidence.

<!-- SOURCE-BLOCK QCP:35 END -->

<!-- SOURCE-BLOCK QCP:36 BEGIN -->

Continue with: [QCP §3](3-observe-network-paths-and-boundary-enforcement.md#QCP_03)  •  [QCP §6](6-build-an-evidence-packet-a-reviewer-can-challenge.md#QCP_06)

<!-- SOURCE-BLOCK QCP:36 END -->

<!-- SOURCE-BLOCK QCP:37 BEGIN -->

<!-- SOURCE-BLOCK QCP:37 END -->

[Previous chapter](1-select-the-qualification-scope-and-acceptance-claim.md) · [Chapter index](README.md) · [Next chapter](3-observe-network-paths-and-boundary-enforcement.md)
