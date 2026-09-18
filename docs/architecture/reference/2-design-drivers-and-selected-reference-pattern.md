# 2. Design drivers and selected reference pattern

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:74 BEGIN -->

<a id="__RefHeading___Toc3642_865363315"></a>
<a id="RA_s_002"></a>

<!-- SOURCE-BLOCK RA:74 END -->

<!-- SOURCE-BLOCK RA:75 BEGIN -->

The design addresses four linked needs: isolate independently administered tenants, deliver capacity without a bespoke infrastructure project for every workload, retain security outcomes across vendor changes, and limit the effect of faults and privileged changes. It assumes that workloads can be compromised, administrators can make mistakes, native defaults can be permissive and shared dependencies can fail. The design therefore separates routing authority, administrative authority, resource ownership and failure domains rather than treating a private network as a trust boundary.

<!-- SOURCE-BLOCK RA:75 END -->

<!-- SOURCE-BLOCK RA:76 BEGIN -->


<a id="source-table-76"></a>

| Driver | Selected architectural response | Consequence |
| --- | --- | --- |
| Tenant scale | Precommissioned hosting cells and attachment capacity; routine tenant state in vendor overlays | Growth adds qualified capacity; a tenant request does not normally reconfigure leaf/spine switches |
| Security separation | Independent domain routing, mandatory workload policy and explicit two-zone ZIP boundaries | No common unrestricted transit path, even where physical equipment is shared |
| Operational control | Separate platform, fabric, edge, management and workload authority | Several scoped provisioning packages replace one all-powerful deployment identity |
| Portability | Stable hosting requirements and service classes, with native vendor realization | Equivalent outcomes, not identical object names, gateways or disk formats |
| Resilience | Site-local failure domains, independent management recovery and reserved surviving capacity | Recovery does not rely on bypassing security or borrowing capacity already promised elsewhere |
| Implementation practicality | Existing management APIs, platform installers and supported automation tools | A new custom portal, scheduler or route-compiler application is not a prerequisite |

<!-- SOURCE-BLOCK RA:76 END -->

<!-- SOURCE-BLOCK RA:77 BEGIN -->

<!-- SOURCE-BLOCK RA:77 END -->

<!-- SOURCE-BLOCK RA:78 BEGIN -->

## Reference choices

<!-- SOURCE-BLOCK RA:78 END -->

<!-- SOURCE-BLOCK RA:79 BEGIN -->

The large-site pattern is a routed leaf/spine fabric with redundant platform and security-edge attachments. Vendor overlays terminate within their own platform boundaries. Independent security domains connect through a provider-operated security-edge service. A separate management environment contains privileged access and infrastructure control endpoints; physically independent OOB access provides the recovery path where supported. Shared service consumers reach selected endpoints, not the whole provider environment.

<!-- SOURCE-BLOCK RA:79 END -->

<!-- SOURCE-BLOCK RA:80 BEGIN -->

The default inter-zone realization is a routed, stateful security-edge service with isolated logical contexts. Distributed enforcement can replace or supplement it only through an explicit equivalence decision covering routing, inspection, authority, logging and failure behaviour. It is not the default simply because a hypervisor offers a distributed firewall. The reference keeps one clear enforcement path while allowing a qualified native implementation where it preserves all boundary functions.

<!-- SOURCE-BLOCK RA:80 END -->

<!-- SOURCE-BLOCK RA:81 BEGIN -->

Confidentiality, integrity and availability impacts remain separate from service performance. A security classification does not select a VLAN, host cluster or uptime percentage by itself. A security profile sets controls; an isolation profile defines allowed sharing; compute and storage classes define resource characteristics; availability and recovery classes define measured service outcomes. These are architecture parameters, whether selected through a catalogue, a form, an API or an approved deployment specification.

<!-- SOURCE-BLOCK RA:81 END -->

<!-- SOURCE-BLOCK RA:82 BEGIN -->

The central trade-off is deliberate: precommissioned infrastructure consumes some reserve capacity, and explicit security boundaries consume routing and inspection resources. In return, routine provisioning has a bounded set of safe choices. Capacity and policy limits are visible before a request is accepted rather than discovered after unrestricted connectivity has been created.

<!-- SOURCE-BLOCK RA:82 END -->

<!-- SOURCE-BLOCK RA:83 BEGIN -->

Related engineering: [GM §2 — Primary knowledge homes and cross-cutting changes](../../assurance/gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md#GM_s_002)

<!-- SOURCE-BLOCK RA:83 END -->

[Previous chapter](1-purpose-scope-and-architectural-authority.md) · [Chapter index](README.md) · [Next chapter](3-system-context-and-physical-hosting-topology.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0003 — Let the infrastructure architecture lead the tooling](../../adr/0003-let-the-infrastructure-architecture-lead-the-tooling.md)
- [ADR-0019 — Separate information impacts from service-level and recovery promises](../../adr/0019-separate-information-impacts-from-service-level-and-recovery-promises.md)

<!-- END GENERATED DECISION LINKS -->
