# 11. Compute pools, hypervisors and workload placement

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:176 BEGIN -->

<a id="__RefHeading___Toc3660_865363315"></a>
<a id="RA_s_011"></a>

<!-- SOURCE-BLOCK RA:176 END -->

<!-- SOURCE-BLOCK RA:177 BEGIN -->

Compute capacity is grouped into qualified pools with explicit hardware characteristics, security-domain eligibility and failure boundaries. The reference separates provider management workloads, security/service infrastructure and tenant workloads. Tenant host pools implement the adopted zone/co-residency policy. Host grouping must be enforced by scheduling, restart and migration controls; naming a cluster or adding a tag is not sufficient.

<!-- SOURCE-BLOCK RA:177 END -->

<!-- SOURCE-BLOCK RA:178 BEGIN -->


<a id="source-table-178"></a>

| Pool characteristic | Architecture requirement | Provisioned realization |
| --- | --- | --- |
| Security eligibility | Known tenant/domain/zone sharing policy and privileged boundary | Cluster or host group membership; enforced placement and mandatory endpoint policy |
| CPU and memory | Defined compatibility, reservations, oversubscription and performance envelope | Approved VM sizes/flavours, reservations and placement constraints |
| Failure containment | Host/rack independence appropriate to the service and surviving capacity | Anti-affinity, restart/evacuation policy and reserved headroom |
| Boot and platform trust | Supported firmware/hypervisor, approved boot mode and required attestation | Verified image/template, firmware baseline, secure boot/TPM controls where applicable |
| Special devices | Explicit accelerator, passthrough, nested virtualization and mobility limitations | Dedicated eligible hosts and restricted device assignment |
| Lifecycle | Supported patch path, maintenance evacuation and retirement | Controlled image/host lifecycle and tested rollback or recovery |

<!-- SOURCE-BLOCK RA:178 END -->

<!-- SOURCE-BLOCK RA:179 BEGIN -->

<!-- SOURCE-BLOCK RA:179 END -->

<!-- SOURCE-BLOCK RA:180 BEGIN -->

CPU, memory and storage are admitted together. A VM is not a valid allocation if its compute is available but its storage class, key service, network attachment or recovery requirement cannot be delivered. The service distinguishes requested resources, guaranteed reservations and observed consumption. Oversubscription is a published service property and must not consume capacity reserved for a security or failure requirement.

<!-- SOURCE-BLOCK RA:180 END -->

<!-- SOURCE-BLOCK RA:181 BEGIN -->

## Placement across vendor stacks

<!-- SOURCE-BLOCK RA:181 END -->

<!-- SOURCE-BLOCK RA:182 BEGIN -->

The provider first selects an eligible site, cell and service class, then uses the platform scheduler within the approved pool. This two-level decision prevents a vendor scheduler from choosing a host outside the security or recovery boundary. New allocation, resize, evacuation, HA restart, restore and migration use the same eligibility rules. If a required dedicated or zone-specific pool is unavailable, the operation pauses or selects another already authorized pool; it does not silently become shared.

<!-- SOURCE-BLOCK RA:182 END -->

<!-- SOURCE-BLOCK RA:183 BEGIN -->

Images and templates are versioned infrastructure inputs. They identify operating system, virtual hardware/boot mode, drivers, protection agents, hardening, provenance, supported lifetime and known limitations. An image may require a separate vendor variant while preserving the same service requirements. The provider governs publishing and retirement; the workload owner remains accountable for application configuration and business data. This is a responsibility boundary, not a design of the application itself.

<!-- SOURCE-BLOCK RA:183 END -->

<!-- SOURCE-BLOCK RA:184 BEGIN -->

The reference does not require every platform to expose identical virtual CPUs, device models, snapshot types or guest tooling. These differences belong in the realization and portability records. Features that constrain exit, such as device passthrough or platform-specific virtual security devices, are declared before allocation and included in the recovery/migration design.

<!-- SOURCE-BLOCK RA:184 END -->

<!-- SOURCE-BLOCK RA:185 BEGIN -->

Related engineering: [VND §2 — Physical placement and the sharing decision](../../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md#VND_s_002)  •  [QUAL §3 — Capacity, service envelopes and growth triggers](../../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)

<!-- SOURCE-BLOCK RA:185 END -->

[Previous chapter](10-addressing-name-services-and-end-to-end-traffic.md) · [Chapter index](README.md) · [Next chapter](12-storage-backup-and-data-isolation-architecture.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0008 — Preserve zone-aware host placement and disclose every shared layer](../../adr/0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md)
- [ADR-0038 — Govern image and privileged dependency provenance across their lifecycle](../../adr/0038-govern-image-and-privileged-dependency-provenance-across-their-lifecycle.md)

<!-- END GENERATED DECISION LINKS -->
