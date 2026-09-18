# Native platform realization and deny-first build sequence

**NRC-M01 supporting procedure — Proposed, not a native command recipe.**
Use the selected release's accepted installer and resource-owner tools. Nothing in this
kit chooses a firewall vendor, provides API credentials or authorizes an apply.

## Common sequence and hold points

| Step | Original stage / ownership | Result and hold point |
| --- | --- | --- |
| NC00 | B14-01 / G0 | Actual site/tuple/sharing/service/test scope reviewed; unresolved mandatory decisions hold the build |
| NC10 | B14-02 / P0 | Independently recoverable bootstrap access and minimum dependencies; record transfer and revocation conditions |
| NC20 | B14-02 / P1 + G1 | Observed fabric/OOB/attachment capacity and its G1 acceptance; installation inventory alone is insufficient |
| NC30 | B14-03 / P2 + P3 | Supported platform and service components installed under restricted authority; not yet advertised as ordinary tenant capacity |
| NC40 | B14-04 / restricted P4 | Owned tenant/domain resources prepared under verified deny; no workload connection before that control is effective |
| NC50 | B14-04 / restricted P5 | Disposable endpoints, healthy probes and explicitly authorized observations; a test exception is not production activation |
| NC55 | Failure/completion cleanup / P6 (B14-08 lifecycle responsibility) | Reconcile owned partial effects and remove temporary test access without waiting for G2/G3; preserve retained copies and keys |
| NC60 | B14-05 / G2 | Exact offered capability, operation coverage and measured service envelope reviewed |
| NC70 | B14-06 / applicable initial G4 | Operating owner/custody, incident/support and required restore/recovery proof established |
| NC80 | B14-07 / separate P4-P5 + G3 | Separate production change with G0/G1/G2, applicable initial G4 and current authority; no activation action exists in this kit |
| NC90 | B14-08 / P6 + recurring G4 | Ongoing observation, requalification and data-safe retirement; recurring exercises never replace initial readiness |

The dependencies describe required planning handoffs, **not an executable scheduler**.
In particular, failed-build containment and cleanup depend on known scope and owners
(NC00), not successful bootstrap, platform installation, denied-domain preparation,
qualification or production activation.
Follow the [safe-stop and cleanup procedure](recovery-retirement.md) for any partial run.
The first restricted platform qualification cannot require an already completed G2 for
that same capability; ordinary tenant consumption does require accepted offered capacity.

## Nutanix

| Phase | Required native engineering | Related candidate source and boundary |
| --- | --- | --- |
| Foundation | Actual AHV/AOS/Prism/Flow/API/provider/feature/entitlement combination, eligible compute/storage, management and bootstrap dependencies | [Commission the hosting cell](../../engineering/platform-build/2-nutanix-commission-the-hosting-cell.md); the repository does not install a complete cell |
| Domain | Administrative project/role/category scope, independent VPC/routing instances, owned overlay subnets and external attachment design | [Domain realization](../../engineering/platform-build/3-nutanix-realize-a-tenant-and-its-workload-domains.md); `nutanix-domain` is not an external security-edge build |
| Workload | Accepted image, identity, placement/storage and mandatory policy; verify actual NIC connection separately from power state | [Workload module](../../../terraform/modules/nutanix-workload/README.md); a task success does not establish quarantine |
| Approved paths | Qualified domain-specific external handoffs and origin-specific service replies; routed/NAT behaviour explicitly selected | [Exact route module](../../../terraform/modules/nutanix-route/README.md); it does not create/qualify the receiving firewall or a full routing service |
| Observe | Exact resource, current VPC/subnet fields, task identity and selected version token; then actual traffic and policy evidence | [Nutanix readback](../../../tools/nutanix_observe.py) is not full Flow/VM/storage inventory, child-task traversal, data-path or HA qualification |

A native `tenantId`, a Prism project and the enterprise tenant identity are not assumed
interchangeable. Show the actual mapping and delegated mutation limits. Record shared
CVM, storage and management dependencies even when guest placement is separated.

## VMware / NSX

| Phase | Required native engineering | Related candidate source and boundary |
| --- | --- | --- |
| Foundation | Actual vSphere/NSX tuple, transport/Edge roles, supported routing/policy hierarchy, placement/storage and protected management | [Commission transport, compute and Edge](../../engineering/platform-build/4-vmware-nsx-commission-transport-compute-and-edge-roles.md); no complete Tier-0/Edge bootstrap is supplied |
| Domain | Tenant authority, Tier-1/segment realization and isolated upstream routing; review connected/distributed shortcuts | [Lifecycle realization](../../engineering/platform-build/5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md); a shared unrestricted upstream is not the reference boundary |
| Workload | Accepted template, eligible resource pools, disks and network identity with effective quarantine before connection | [vSphere workload module](../../../terraform/modules/vsphere-workload/README.md); do not infer an unsupported power-state switch |
| Approved paths | Owned gateway policy and upstream edge paths, explicit IPv4/IPv6 handling and origin-specific returns | [Gateway quarantine](../../../terraform/modules/nsx-gateway-quarantine/README.md) and [exact route](../../../terraform/modules/nsx-route/README.md) are bounded components, not complete ZIP equivalence |
| Observe | Selected Policy configuration, revision and intent realization, plus the actual enforcement locations and traffic | [NSX observer](../../../tools/nsx_observe.py) does not prove all transport-node rules, dynamic membership or alternate forwarding paths |

Do not assume a configuration revision equals the expected intent version. Distinguish
aggregate realization, runtime state and observed packet behaviour. Test same-host
paths, upstream routing, policy priority, group ownership and return traffic explicitly.

## OpenStack

| Phase | Required native engineering | Related candidate source and boundary |
| --- | --- | --- |
| Foundation | Actual distribution and Nova/Neutron/Cinder/identity services, backend, API policy, scheduler and storage combination | [Commission a distribution](../../engineering/platform-build/6-openstack-commission-a-distribution-not-a-generic-label.md); service names alone are not an installed tuple |
| Domain | Independent project/domain routing scope, provider-owned mandatory controls, port security and approved source identities | [Network-mutation ownership](../../engineering/platform-build/7-openstack-protect-mandatory-network-mutation.md); additive tenant allow groups do not create a mandatory deny hierarchy |
| Workload | Accepted image/flavour, boot/data volume ownership, explicit security-group association and eligible placement | [Workload module](../../../terraform/modules/openstack-workload/README.md); preserve retained data, and observe actual port/guest behaviour |
| Approved paths | Provider-controlled external attachments and qualified security-edge handoffs, with symmetric owned replies | [Exact route module](../../../terraform/modules/openstack-route/README.md); no complete external gateway/firewall service is provided |
| Observe | Exact owned Neutron network/router/subnet/port/group configuration and tenant binding | [Neutron observer](../../../tools/neutron_observe.py) is not full compute/storage inventory or enforcement/failover proof |

Test the real delegated role against attempts to replace mandatory groups, alter port
security, source identities or external attachments. Do not write directly into a network
backend while leaving Neutron as a competing owner of the same objects.

## Per-operation receipt

For each separately authorized native action record actual scope/generation, owner and
executor, input/plan/lock references, native task/resource identities, observed changes
and the next permitted hold point. Keep credentials and raw state outside Git. A saved
Terraform plan may itself be sensitive. Import/adoption, replacement and deletion need
separate lifecycle review; do not infer them from a successful create operation.

[Kit index](README.md) · [Native observation campaign](campaign.md)
