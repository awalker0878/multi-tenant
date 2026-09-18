# 23. Tenant, domain and workload provisioning sequence

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3684_865363315"></a>
<a id="RA_s_023"></a>

The consumer supplies the required hosting environment, not the vendor topology. Minimum inputs are accountable tenant/service ownership; confidentiality, integrity and availability context; requested compute/storage classes; zone membership; permitted service flows; shared-service needs; external exposure; availability/recovery and location constraints; and lifecycle/retention requirements. These can be captured in a human-readable deployment specification and translated to automation inputs. Detailed schema design belongs to the implementation annex.


<a id="source-table-325"></a>

| Step | Infrastructure action | Gate and safe failure state |
| --- | --- | --- |
| 1 — Admit | Check requester authority, approved profiles, quotas, security-zone relationships and declared dependencies | Reject before resource allocation if mandatory requirements conflict |
| 2 — Place and reserve | Select eligible site/cell/pools; reserve compute, storage, addresses and isolated attachment/edge capacity | Reservation has an owner and expiry; no invented address or unqualified target |
| 3 — Establish scope | Create/reuse entitled tenant scope and approved domain instances; assign accountable ownership | Shared domains are not owned exclusively by one retiring WSD |
| 4 — Build denied networks | Create native networks, gateways and domain attachments with mandatory baseline already effective | Endpoints remain absent, disconnected or quarantined until enforcement exists |
| 5 — Establish boundary | Create the paired edge context/association, exact routes and approved policy under edge authority | No alternate native route or uninspected default; return path verified |
| 6 — Provision resources | Allocate approved image/VMs and data objects in eligible pools; attach only authorized networks/storage | Failed placement or attachment does not relax isolation or reassign another tenant’s resource |
| 7 — Attach services | Register names, identity, logging, keys and backup/protection; enable approved service bindings | Required initialization traffic is narrow and attributable; no broad shared-subnet permit |
| 8 — Verify internally | Check health, ownership, policy, route paths, service access, management denial and recovery/protection assignments | Failed or unknown checks keep the environment restricted |
| 9 — Activate | Enable only the approved external exposure/production connections; verify the live service path | Activation is reversible; failed external checks withdraw exposure without destroying data |
| 10 — Hand over | Record as-built resources, responsibilities, evidence and accepted operating conditions | Service Ready only when the delivered scope and required authorization conditions are satisfied |

The forward sequence is not one atomic transaction. A cloud API may accept a request before routing or policy is realized, and a runner can lose a response after a resource was created. Operations therefore keep stable request/resource identities, discover actual state and resume or safely compensate. Capacity, address and attachment reservations are reconciled rather than leaked or duplicated.

## Cross-stack example

Consider a tenant requesting one internal OZ network, one RZ network, compute in both, protected storage, DNS/time/logging/backup and one approved OZ-to-RZ service flow, with no Internet exposure. On Nutanix, the domain realization uses separate qualified VPC contexts and Flow policy. On VMware/NSX, it uses segments, Tier-1s and isolated upstream contexts. On OpenStack, it uses separate Neutron domain contexts, ports and baseline security controls. All three also require the provider ZIP, authoritative addresses/names, protection service and evidence under their respective owners.

The requirement and acceptance outcome remain the same; the native build steps differ. Creating VMs successfully on each platform is not enough. The deployment must also demonstrate that the intended inter-zone flow works, unapproved paths are denied, management is unreachable from workloads, storage/protection ownership is correct, and later changes and retirement clean up the associated resources.

## Updates to an existing environment

A resize within entitled pools follows the normal resource-change path. Adding a zone, new partner relationship, public exposure or a different isolation profile requires renewed architecture/security evaluation. Changed plans must match current resource state and approval. An emergency containment action remains authoritative until explicitly released; ordinary reconciliation must not restore the old allow path behind the incident owner’s back.

Related engineering: [PROV §4 — End-to-end fixture provisioning and safe activation](../../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md#PROV_s_004)  •  [VND §1 — One reference environment, three native realizations](../../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md#VND_s_001)

[Previous chapter](22-vendor-platform-and-shared-service-commissioning.md) · [Chapter index](README.md) · [Next chapter](24-terraform-across-the-vendor-stacks.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0015 — Build under deny and verify before and after activation](../../adr/0015-build-under-deny-and-verify-before-and-after-activation.md)
- [ADR-0031 — Discover uncertain native outcomes instead of blind replay or rollback](../../adr/0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md)

<!-- END GENERATED DECISION LINKS -->
