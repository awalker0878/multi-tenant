# 7. OpenStack: protect mandatory network mutation

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Platform_Engineering_and_Build_Specifications.docx) · [Chapter index](README.md)

> **Source:** PBS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8c2dd9e86b4ea021922777a963534c6b52d85dff8ee398c3a12cc81287356643 -->
<!-- SOURCE-BLOCK PBS:84 BEGIN -->

<a id="PBS_07"></a>

<!-- SOURCE-BLOCK PBS:84 END -->

<!-- SOURCE-BLOCK PBS:85 BEGIN -->

The base service uses provider-owned control of mandatory network policy and external attachment. Tenant self-service is bounded by the offered capability, not by permissive native defaults.

<!-- SOURCE-BLOCK PBS:85 END -->

<!-- SOURCE-BLOCK PBS:86 BEGIN -->

Design basis and related records: [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)  •  [WD §8](../../solutions/internal-protected-workload/8-mapping-the-schedules-into-each-vendor-stack.md#WD14_S08)  •  [VC §4](../vendor-cards/4-openstack-realization-card.md#VC_04)

<!-- SOURCE-BLOCK PBS:86 END -->

<!-- SOURCE-BLOCK PBS:87 BEGIN -->

Neutron describes security groups as additive allow rules, including default egress permissions. It also documents the effect of disabling port security and notes that removing egress may prevent metadata access. Accordingly, preserve required initialization explicitly and verify effective permission across every attached group; do not treat an added group as a mandatory deny layer. \[D02\]

<!-- SOURCE-BLOCK PBS:87 END -->

<!-- SOURCE-BLOCK PBS:88 BEGIN -->

Verified mechanism source: [D02 — OpenStack Neutron networking concepts](https://docs.openstack.org/neutron/latest/admin/intro-os-networking.html)

<!-- SOURCE-BLOCK PBS:88 END -->

<!-- SOURCE-BLOCK PBS:89 BEGIN -->


<a id="source-table-89"></a>

| Mutation surface | Base design ownership | Required negative and positive observation |
| --- | --- | --- |
| Groups and membership | Provider controls mandatory group rules and which groups protect each port. | Tenant cannot add a broader rule or group; the approved workload flow still operates. |
| Port security / address pairs | Provider controls disabling security, additional source identities and relevant exceptions. | Unapproved changes fail through actual API roles; legitimate configured service behaviour remains functional. |
| External attachments | Provider controls external router, provider network, additional NIC and floating-address paths. | Tenant cannot create an escape route; authorized service exposure follows its own design. |
| Initialization | Named metadata/DHCP/DNS and identity needs are allowed only for their actual consumers. | Secure bootstrapping succeeds without broad Internet or provider-management access. |

<!-- SOURCE-BLOCK PBS:89 END -->

<!-- SOURCE-BLOCK PBS:90 BEGIN -->

<!-- SOURCE-BLOCK PBS:90 END -->

<!-- SOURCE-BLOCK PBS:91 BEGIN -->

Build sequence: establish project/roles and quotas; reserve addresses and attachment capacity; create denied domain networks, subnets, ports and separate router contexts; establish the qualified ZIP routes and policy; then attach instances, owned volumes and required services. Observe native readiness before relying on asynchronous deletion or route changes.

<!-- SOURCE-BLOCK PBS:91 END -->

<!-- SOURCE-BLOCK PBS:92 BEGIN -->

Test with the actual delegated tenant role, not an administrator account labelled “tenant”. An inability to enforce the baseline at the selected API/policy boundary blocks that delegated capability. Direct tenant network editing can be a separately qualified extension, but it does not silently become the base service.

<!-- SOURCE-BLOCK PBS:92 END -->

<!-- SOURCE-BLOCK PBS:93 BEGIN -->

Continue with: [QCP §4](../../assurance/qualification-campaign/4-observe-identity-storage-and-protocol-completeness.md#QCP_04)  •  [OPS §3](../../operations/recovery-transition/3-run-maintenance-and-recover-interrupted-changes.md#OPS_03)

<!-- SOURCE-BLOCK PBS:93 END -->

<!-- SOURCE-BLOCK PBS:94 BEGIN -->

<!-- SOURCE-BLOCK PBS:94 END -->

[Previous chapter](6-openstack-commission-a-distribution-not-a-generic-label.md) · [Chapter index](README.md) · [Next chapter](8-publish-shared-service-handoffs-without-sharing-authority.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0023 — Protect mandatory policy and identity selectors from tenant mutation](../../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md)
- [ADR-0026 — Choose and own the actual OpenStack backend and domain boundaries](../../adr/0026-choose-and-own-the-actual-openstack-backend-and-domain-boundaries.md)

<!-- END GENERATED DECISION LINKS -->
