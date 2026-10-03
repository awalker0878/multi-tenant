# Environment coverage and platform completion requirements

[Delivery program](README.md) · [Repository audit](../../assurance/automation-baseline-audit.md) · [Completion backlog](completion-backlog.md)

For current code, use [WSD deployment](wsd-deployment.md), [native guest configuration](native-guests.md) and [package status](progress.md). The matrices below retain the completion requirements derived from the baseline audit; they do not supersede the delivery record.

## Coverage model

An environment is not just a Terraform directory named after a vendor. Track an actual **site/cell + installed platform tuple + lifecycle target + tenant/WSD + zone/security profile + address family + service/recovery offer**. Every offered combination needs supported inputs, owned automation, tests and operating evidence. Do not declare every possible combination supported by taking a Cartesian product of labels.

The [current architecture](../../architecture/reference/7-tenant-environments-and-security-domain-placement.md) separates tenant administration, WSD lifecycle, logical security domain and site/platform domain instance. Preserve those distinctions. A Terraform workspace name or Ansible inventory group alone does not enforce security or placement isolation.

## Core platform and common-layer matrix

**Partial** means a bounded implementation exists. **Documented** means design/procedure/validation exists but no complete executor was found. **Open** means implementation or operational evidence is still required. None of the rows below is native-qualified at the audit baseline.

| Layer / outcome | Nutanix AHV/Flow | VMware vSphere/NSX | OpenStack | Completion work |
| --- | --- | --- | --- | --- |
| P0 automation, trust and state | Documented | Documented | Documented | W02–W04: trusted runner, secrets, state service, inventory and recovery |
| P1 physical fabric/OOB | Documented common infrastructure | Documented common infrastructure | Documented common infrastructure | W05: selected devices, interface schedules, underlay, attachment and failure checks |
| P2 platform installation | Documented | Documented | Documented | W06–W07: supported installer/lifecycle adapter and observed commissioned capacity |
| Tenant entitlement/RBAC/quota | Supplied project reference; incomplete | Supplied pool/network references; incomplete | Supplied project/flavor/AZ references; incomplete | W09: actual administrative ownership and mutation limits |
| P4 domain/quarantine | Partial VPC/subnet/category/Flow | Partial Tier-1/segment/group/DFW | Partial network/subnet/router/group | W12, W15: ordered composition and native policy proof |
| P5 VM and block storage | Partial off/disconnected VM | Partial clone onto accepted quarantine; may power on | Partial shutoff VM/down port and Cinder volumes | W12–W14: supported image, bootstrap, configuration and service binding |
| Security edge / ZIP | Documented; route assumes attachment | Partial gateway quarantine; full edge absent | Domain/route fragments; full edge absent | W08, W15: selected edge, context, attachment, HA, inspection and replies |
| Foundation service consumption | Documented + evidence validators | Documented + evidence validators | Documented + evidence validators | W07, W10–W14: working DNS/time/trust/key/log/backup integrations |
| Native observation | Partial VPC/subnet/tasks, explicit task tree | Partial NSX configuration/realization | Partial Neutron exact-ID readback | W16: complete supported resource/operation coverage |
| Controlled activation | Open | Open | Open | W18–W20: prepared-to-restricted-to-active transitions and withdrawal |
| Day-2 and retirement | Documented + bounded reviewers | Documented + bounded reviewers | Documented + bounded reviewers | W17, W21–W25: real lifecycle actions, observations and retention-aware cleanup |

### Nutanix-specific work

| Area | Required deliverable | Native completion evidence |
| --- | --- | --- |
| Hosting cell | Selected AOS/AHV/Prism/Flow/API/firmware/licence tuple; supported installation/registration, cluster/storage/network settings, management trust and lifecycle adapter | Fresh installation or accepted brownfield adoption; host/CVM/storage failure tests and protected management |
| Tenant foundation | Project/role/quota/category ownership, supported placement controls, image/storage-container handoffs, protection/key integration | Delegated user cannot mutate mandatory categories/policy or allocate outside eligible capacity |
| Network/edge | Actual external subnet and VPC attachment implementation, owned route table and return paths, supported Flow policies and selected edge functions | Cross-tenant denial, same-host and same-subnet denial, permitted own-tenant path, no alternate/bypass route, edge failover |
| Workload/configuration | Isolated first boot and IP/DNS/initialization, image-based configuration, supported guest roles and enrollment; controlled NIC/power transition | Useful guest reachable only over allowed bootstrap paths; repeated run converges; no exposure before quarantine |
| Lifecycle/readback | VM, disk, NIC, category, Flow, project and relevant storage observations in addition to VPC/subnet/task support; task receipts and asynchronous recovery | Lost response, partial task tree, failed child, concurrent change, resize, restore and retirement handled without duplicate or unsafe resources |

Source basis: [Nutanix commissioning](../../engineering/platform-build/2-nutanix-commission-the-hosting-cell.md), [tenant realization](../../engineering/platform-build/3-nutanix-realize-a-tenant-and-its-workload-domains.md), [task-tree implementation](../nutanix-task-tree-readback.md).

### VMware/NSX-specific work

| Area | Required deliverable | Native completion evidence |
| --- | --- | --- |
| Hosting cell | Supported ESXi/vCenter/NSX tuple, cluster/storage settings, zone-eligible pools, transport nodes/zones, uplink/TEP/MTU and Edge installation | Compute, storage, management and transport health; supported failover/evacuation preserves placement |
| Tenant foundation | Resource-pool/folder/role/quota or equivalent entitlement mapping, protected image/template and policy ownership | Tenant cannot escape pool/datastore/network scope or change provider-owned policy membership |
| Routing/security | Isolated upstream design, Edge/Tier-0 or other accepted context, Tier-1 attachments, gateway/distributed policy and approved service returns | No common upstream transit shortcut; connected routes, priority, exclusions, group membership and HA paths verified |
| Workload/configuration | Resolve NSX segment to vCenter network ID, qualify supported template layout and guest customization, configure/enroll guest through restricted paths | Quarantine proven **before cloning**; clone may power on; unsupported template layouts fail preflight |
| Lifecycle/readback | vSphere VM/NIC/disk/datastore/storage-policy and placement readback alongside NSX realization; supported migration/adoption/update/retirement | API configuration agrees with actual enforcement; retained disks have accountable custody; mobility and recovery preserve isolation |

Source basis: [VMware/NSX commissioning](../../engineering/platform-build/4-vmware-nsx-commission-transport-compute-and-edge-roles.md), [policy lifecycle](../../engineering/platform-build/5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md), [vSphere constraints](../../../terraform/modules/vsphere-workload/README.md).

### OpenStack-specific work

| Area | Required deliverable | Native completion evidence |
| --- | --- | --- |
| Hosting cell | Select distribution/release and supported deployment tool; configure required Keystone/Nova/Neutron/Glance/Cinder services, network/storage backends, placement and protected management | Fresh install or accepted adoption, service health and controller/compute/network/storage failure recovery |
| Tenant foundation | Keystone project/domain/roles, scoped automation credentials, quotas, flavors, images, AZ/host eligibility, volume types and encryption/key integration | Real delegated roles cannot alter mandatory port security/groups, allowed source identities or external attachments |
| Routing/security | Provider-owned enforcement, supported external gateway/security-edge integration, selected DHCP/metadata behavior and return paths | Tenant-added allow groups cannot defeat required isolation; no competing direct backend writer; no unintended metadata/egress path |
| Workload/configuration | Coordinate network/router/port activation and VM bootstrap; accepted image initialization, guest roles and service enrollment | Safe first boot, retained boot/data volumes, correct project identity and independent guest/data access checks |
| Lifecycle/readback | Add Nova/Cinder/Keystone coverage and Ansible Neutron dispatch; reconcile asynchronous build/attach/delete and partial volumes/ports | Import, resize, rebuild, restore, failure recovery and retirement preserve ownership and retained data |

Source basis: [distribution commissioning](../../engineering/platform-build/6-openstack-commission-a-distribution-not-a-generic-label.md), [mandatory network ownership](../../engineering/platform-build/7-openstack-protect-mandatory-network-mutation.md), [Neutron observer](../../../provisioner/execution/neutron_observe.py).

## Lifecycle targets

These are required planning distinctions, not a claim that named environments are already configured. W01 must choose and enumerate actual target instances. Reuse the same approved modules and roles with separately accepted inputs and authority.

| Target | Purpose and separation | Completion requirement |
| --- | --- | --- |
| Local CI / synthetic labs | No native endpoints or live credentials | Retain current regression coverage; never treat fixture output as an installed service |
| Restricted native qualification | Disposable targets under bounded contact/change authority | Real creation, configuration, positive/negative paths, failure/recovery and cleanup on each selected tuple |
| Development/test | Routine non-production allocations from accepted capacity | Dedicated state/inventory/credentials and quotas; safe defaults and same mandatory security controls |
| Pre-production, if offered | Rehearse the offered production topology and change process | Promote identical tested code/toolchain; prove realistic upgrade, restoration and withdrawal |
| Production | Accepted service envelope with operating owner and authority | Exact approved plan, current readiness, post-change path verification, monitoring and rollback/withdrawal |
| Recovery target, if offered | Restore/failover without weakening placement or security | Eligible target capacity, independent state/key/catalogue dependencies, isolated restore and measured recovery objectives |

Site recovery can be outside a particular service offer only by an explicit scope decision. Applicable backup, management recovery, state recovery, retention and continuity work still remains.

## Service/security profile decisions

| Profile | Current repository scope | Work required before offering it |
| --- | --- | --- |
| Internal OZ/RZ IPv4 | Four-domain, two-tenant reference design plus candidate IPv4 modules | Complete W01–W27; qualify the full connected fixture on all three stacks |
| IPv6-only / dual-stack | Real Linux packet fixtures; native capability remains unqualified | W19: native network/addressing/routes/policy/services, neighbor/RA/DHCPv6 behavior as selected, MTU/PMTU, no hidden IPv4 fallback; retain independent IPv4 evidence for dual-stack |
| Public PAZ/OZ/RZ | Proposed maintained design profile | W28: full design, ingress/WAF/load-balancing as selected, certificates, public DNS, backend policy, capacity, withdrawal and native qualification |
| Controlled egress | Architecture requires separately scoped approval | W15/W28 as applicable: actual proxy/NAT/inspection, identity, reply ownership and fail-closed behavior; ingress approval does not grant egress |
| Higher-assurance/HRZ or dedicated variants | Bounded extension/adoption framework | W29: explicit physical/logical sharing decision, eligible pools, management/storage/edge/key isolation and target-specific qualification |
| Bare metal, containers, accelerators, L2 stretch, cross-stack or future platforms | Extension evidence model, not completed baseline automation | W29: explicit adoption, dedicated implementation and operation coverage; do not report as delivered by the three VM stacks |

Public cloud, Hyper-V and Proxmox are not additional implemented baseline families in this repository. Adding them is an explicit scope extension. Supporting every environment means completing every **declared offer**, and clearly identifying unsupported combinations.
