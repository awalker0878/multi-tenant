# 5. VMware/NSX: bind domain, workload and policy lifecycles

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Platform_Engineering_and_Build_Specifications.docx) · [Chapter index](README.md)

> **Source:** PBS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8c2dd9e86b4ea021922777a963534c6b52d85dff8ee398c3a12cc81287356643 -->
<a id="PBS_05"></a>

The provisioning workflow coordinates vSphere resources, NSX resources and independently owned shared services; it does not merge their privileges into one unrestricted state.

Design basis and related records: [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)  •  [WD §8](../../solutions/internal-protected-workload/8-mapping-the-schedules-into-each-vendor-stack.md#WD14_S08)


<a id="source-table-64"></a>

| Object group | Create / change responsibility | Required cross-owner evidence |
| --- | --- | --- |
| Domain networking | NSX owner allocates segments, per-domain Tier-1 and the approved isolated upstream association. | Actual upstream route context and no unintended propagation between domains. |
| Mandatory segmentation | Security/platform owner establishes protected groups, membership and effective policy. | Same-host and cross-host denial plus the specifically approved flow. |
| ZIP handoff | Edge owner configures paired attachments, routes, stateful policy and required services. | F14-01 request and reply follow the accepted native and external enforcement path. |
| VM and storage | vSphere/data owners allocate approved image, eligible placement and owned disks. | Correct host eligibility, storage/key policy and protection assignment. |
| Activation | Service owner checks current technical evidence, initial G4 and authority. | Approved live endpoint works; failure withdraws exposure without deleting data. |

The LLD maps each logical WD domain to its actual native gateway, segment, route advertisement and external attachment. Do not infer an appliance hop merely from a Tier-1 object. Compare connected routes, distributed routing, service-router functions, gateway policies and the chosen external security path.

Live mobility and HA restart remain inside the accepted compute, storage and zone/co-residency boundaries. A shared datastore does not automatically make every host an eligible recovery target. Review route/policy membership after relocation and include required keys and virtual-device compatibility in restore and exit testing.

## Lifecycle release record

Supply separate operation coverage for VM customization, resize, disk replacement, segment changes, routing-policy changes and gateway mode changes. State import is only ownership adoption after review, not proof of conformance or authorization to replace a live gateway. Preserve former configuration and supported recovery choices before an irreversible change.

Continue with: [QCP §3](../../assurance/qualification-campaign/3-observe-network-paths-and-boundary-enforcement.md#QCP_03)  •  [QCP §7](../../assurance/qualification-campaign/7-compare-vendor-realizations-without-assuming-migration.md#QCP_07)  •  [OPS §3](../../operations/recovery-transition/3-run-maintenance-and-recover-interrupted-changes.md#OPS_03)

[Previous chapter](4-vmware-nsx-commission-transport-compute-and-edge-roles.md) · [Chapter index](README.md) · [Next chapter](6-openstack-commission-a-distribution-not-a-generic-label.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0025 — Use isolated NSX upstream routing rather than a common unrestricted table](../../adr/0025-use-isolated-nsx-upstream-routing-rather-than-a-common-unrestricted-table.md)

<!-- END GENERATED DECISION LINKS -->
