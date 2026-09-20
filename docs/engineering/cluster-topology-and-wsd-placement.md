# Cluster topology and WSD placement

**Status:** Proposed design elaboration; no site adoption or native qualification implied.

**Date:** 2026-09-20. Reviewed against repository revision `be492784c8f935eaa5895c973f3ff77ffd5eb622`. The original 1.0 audit snapshot remains a historical assessment of its stated revision.

[1.0 index](../implementation/automation/README.md) · [Environment coverage](../implementation/automation/environments.md) · [Completion backlog](../implementation/automation/completion-backlog.md)

## 1. The WSD consumes qualified cluster capacity

A Workload Security Domain (WSD) is a bounded service environment with an owner, lifecycle, security requirements and recovery obligations. A physical cluster is a provider resource and failure/lifecycle boundary. Their relationship is many-to-many: one WSD can consume several eligible clusters; one cluster can host allocations from several compatible WSDs.

For example, an internal WSD can have OZ processing resources on an OZ workload cluster, RZ data resources on an RZ workload cluster, independent native routing/policy instances, separately entitled service bindings and equivalent eligible recovery allocations. Creating the WSD ordinarily consumes already commissioned capacity. It does not create a new physical cluster, rebuild the management plane or acquire new fabric equipment.

This follows the existing [hosting-cell model](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md), [tenant/domain model](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) and [placement requirements](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md). A hosting cell may contain or depend on several clusters/services and is not synonymous with a vendor cluster or an OpenStack Nova cell.

## 2. Distinguish four meanings of cluster

| Cluster meaning | What it groups | Relation to a WSD |
| --- | --- | --- |
| Physical virtualization/HCI cluster | Hosts, scheduler/HA behavior and sometimes integrated storage/controllers | Supplies eligible compute/storage; can serve compatible WSDs |
| Platform control or service HA cluster | Replicas of managers, controllers, identity, DNS, logging or another service | Supplies management or a bounded service; its replica count is not the physical host count |
| Storage/protection cluster | Data controllers, storage nodes, repositories and associated metadata/key dependencies | Supplies data or recovery classes with separate ownership and retention |
| Workload-level cluster | An application's database, Kubernetes or other clustered workload | Belongs to an offered workload service within a WSD; does not replace infrastructure placement/isolation |

Three manager VMs on one physical host do not provide three independent host failure domains. Conversely, a three-host cluster is not automatically a supported three-member control-plane deployment. The installed product, service availability and failure model determine both counts.

## 3. Cluster roles to plan

The following are **capacity roles**, not an instruction to procure one identical physical cluster for every row. Each role must map to named physical resources and known administrative, storage and recovery dependencies. Combine roles only when the adopted security and failure model permits it.

| Role | What it hosts or provides | Recommended separation and sharing rule | When needed |
| --- | --- | --- | --- |
| Management and automation | Platform managers, privileged access, scoped runners, state/inventory services and management tooling | Dedicated management capacity, partitioned by administered trust/zone boundary; no tenant workloads or unrestricted universal admin identity | Every deployment needs the function; actual cluster count follows management boundaries |
| Security-edge execution | Boundary gateways/firewalls, required inspection and service-edge routing | Separately governed physical appliances or eligible dedicated virtualization capacity; tenant compute cannot disable/bypass its enforcement | Whenever a WSD communicates across a required boundary |
| Tenant-consumable foundation services | Resolver/time endpoints, artifact distribution, telemetry ingestion and other approved service endpoints | Provider-operated capacity with per-consumer entitlement; divide incompatible zones/trust domains; keep consumption separate from administration | Shared services required by the offer, possibly supplied by existing external services |
| Identity and cryptographic trust | Directory/issuer services, secrets, key management and recovery trust | Separate privilege/custody and recoverable placement; use dedicated capacity/appliances where the assurance profile requires it; do not automatically place roots of trust beside every service consumer | Every offer needs the applicable trust functions; a separate new physical cluster is conditional |
| OZ workload capacity | Approved processing/application workloads in OZ | Physical hosts eligible for OZ; compatible tenants/WSDs may share while native networks, policy and entitlement remain isolated | Internal processing offer |
| RZ workload capacity | Workloads whose approved placement is RZ, including protected data-service tiers where selected | Separate RZ-eligible hosts from OZ in the reference baseline; assess storage/controllers and management sharing as well | WSDs requiring RZ |
| PAZ workload/ingress capacity | Approved externally reachable frontends, proxies and ingress functions | PAZ-eligible capacity distinct from OZ/RZ; public exposure and downstream access are separately controlled | Public-facing offer only; the external Public Zone is not a provider workload cluster |
| Higher-assurance or dedicated workload capacity | Workloads with additional physical/administrative dedication or an adopted HRZ profile | Explicit dedication dimensions and supported controls; a dedicated compute cluster alone does not isolate shared storage, keys or administrators | When the accepted WSD profile requires it |
| Data-service capacity | Guest-facing file/object/block services and, where selected, disaggregated storage | Independently sized storage service with scoped namespaces/keys and controlled data paths; integrated HCI VM storage need not be duplicated as an extra cluster | According to the storage offer and selected platform |
| Backup/protection capacity | Backup control/catalogue, data movers, retained repositories and protected copies | Independent protection/delete authority and required failure separation from primary storage; proxies and repositories can have different placements | According to the protection offer; no new backup cluster per WSD |
| Recovery capacity | Eligible replacement compute/storage and required management/edge/services at the recovery location | Preserve original zone, trust and data obligations; reserve or contract capacity and test dependency recovery | When recovery beyond the surviving primary capacity is promised |
| Qualification and isolated recovery-test capacity | Native release testing, failure experiments and isolated useful-data restore | Restricted targets/probes and representative topology; dedicate physical resources where tests can affect the shared platform or involve untrusted restored workloads | Required qualification/testing function; one permanent universal lab cluster is not assumed |

Do not interpret this table as one broad provider-services network or one broadly trusted management cluster. The [existing management design](../architecture/reference/6-management-platform-control-and-out-of-band-access.md) requires separate authority and recovery paths; the [shared-service design](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) separates consumption, backend and administration.

## 4. Security boundaries determine physical placement

For the initial design, retain separate OZ and RZ physical workload hosts, and add PAZ capacity only if the service is offered. Cyber Centre guidance strongly recommends separating VMs from different network security zones on physical hardware. It also recommends zone-specific physically separate management and virtualization-storage networks and segregated boundary enforcement. These are broader considerations than guest VLAN/VPC separation. A consolidated management/HCI/storage implementation needs an explicit applicability and tailoring decision; this proposal does not declare it compliant merely because it uses microsegmentation. [ITSP.70.010, section 3](https://www.cyber.gc.ca/en/guidance/cyber-centre-data-centre-virtualization-report-best-practices-data-centre-virtualization).

Information categorization, network zone, tenant identity and lifecycle environment are separate dimensions. A Protected B label alone does not determine the zone, and a development label does not authorize weaker controls. Matching an OZ or RZ label alone is insufficient permission for co-residency.

Evaluate whether two allocations can share using their administrative trust, adopted zone/co-residency policy, tenant compatibility, failure impact, resource contention, maintenance cadence, platform features and recovery needs. A new dedicated cluster is justified when those requirements cannot be met by an existing eligible pool, not just because a new WSD or department exists.

## 5. Concrete two-WSD example

The IDs below are symbolic planning identifiers, not real clusters or approved site inputs. This extends the existing internal two-tenant OZ/RZ fixture without assuming public ingress.

| Physical capacity | WSD-A allocation | WSD-B allocation | What remains independent |
| --- | --- | --- | --- |
| Site-1 OZ workload cluster | WSD-A OZ compute/network allocation | WSD-B OZ compute/network allocation | Native domain/routing, mandatory policy, resource ownership and admitted capacity |
| Site-1 RZ workload cluster | WSD-A RZ compute/storage allocation | WSD-B RZ compute/storage allocation | Native domain/routing, data entitlement/keys as required, policy and admitted capacity |
| Qualified security-edge capacity | WSD-A OZ↔RZ boundary and service paths | WSD-B OZ↔RZ boundary and service paths | Boundary authorities, policy/route contexts and origin-specific return paths |
| Qualified foundation/data services | WSD-A service bindings | WSD-B service bindings | Service identity, namespaces, operations, quotas and consumption paths |
| Protection service | WSD-A policy, catalogue/copy ownership and recovery scope | WSD-B policy, catalogue/copy ownership and recovery scope | Retention, keys, restore/delete authority and copy lineage |
| Site-2 eligible OZ/RZ capacity, if offered | WSD-A separately scoped recovery placements | WSD-B separately scoped recovery placements | Original placement constraints, recovery reservations and source-writer exclusion |

In this example there are two WSDs, four primary native domain instances and two primary workload clusters. The management, edge, service and protection capacities are additional dependencies whose actual physical counts must still be designed. Sharing two workload clusters does not establish four independent physical failure domains.

WSD-A and WSD-B can each scale across additional eligible clusters. Placement rules must still hold during HA restart, evacuation, resizing, migration and restore. Lack of eligible surviving capacity leads to a hold or another accepted placement, not an automatic move across a zone boundary.

## 6. Mapping to the three platform families

| Family | Physical/control mapping to specify | WSD mapping to implement |
| --- | --- | --- |
| Nutanix | Separate eligible AHV/HCI clusters where required; document each cluster's controller/storage scope, selected Prism management authority and edge/service dependencies | Project/role/category ownership, separate domain VPC/subnet/policy instances where designed, eligible VM/storage placement and protection/service bindings |
| VMware/NSX | Eligible vSphere clusters/hosts and datastores; explicit vCenter/NSX administrative scope; supported dedicated Edge realization and management placement | Resource-pool/folder/role allocation plus independent NSX domain/segment/policy realization, placement constraints, disks and service bindings |
| OpenStack | Selected control-plane deployment, eligible compute host groups, actual network/security and storage backend separation; assess whether separate deployments/cells are required by administrative/failure scope | Keystone project/RBAC/quotas, eligible scheduling, Neutron domain/policy objects, Nova/Cinder resources and service bindings |

These are proposed realization requirements, not assertions that current modules implement all of them. A resource pool, project, VPC, host aggregate or availability-zone label alone is not proof of physical or administrative independence. OpenStack's availability-zone mechanism relies on configured host/placement aggregate membership; verify actual scheduler enforcement and backend/control dependencies. [Nova availability-zone documentation](https://docs.openstack.org/nova/latest/admin/availability-zones.html).

For HCI, a disk inside a workload cluster and a separately operated file/object endpoint are different services. Preserve the [storage path and controller analysis](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md). Do not count a snapshot on the same primary storage as an independently recoverable backup merely because another service manages it.

## 7. Management, bootstrap and recovery dependencies

Design management as several scoped authorities and recoverable services. Any shared manager or automation platform is a shared compromise/failure dependency even when it manages physically separate workload clusters. Separate management instances/hosting may be required; a common dashboard does not authorize cross-zone management connectivity.

Ensure a viable recovery path for the minimum identity, name/time, secrets/keys, state, backup catalogue and tooling needed to rebuild the environment. Some functions may use independent appliances, a recovery location or controlled offline recovery material. This does not require every dependency to become a new physical cluster, but all replicas cannot depend exclusively on the infrastructure they are needed to restore.

Recovery reproduces required eligible capacity and services, not necessarily identical hardware counts. A single mixed-zone recovery cluster is not an acceptable default for a primary design that required physical zone separation. Avoid assuming a stretched cluster or a shared storage backend provides independent site recovery. Document source and target power, network, control, storage, identity/key and protection dependencies.

Quarantine is normally a controlled state of an allocation within its eligible zone/profile. It does not automatically require a generic quarantine cluster that mixes incompatible workloads. Cyber recovery involving potentially compromised systems may need separately governed clean recovery capacity and a different procedure.

## 8. Cluster catalogue and WSD placement schedule

Add two linked engineering records under W01/W05/W06/W09 before composing the native deployment. These are infrastructure schedules, not a prescription for a custom API/controller.

| Record | Required content |
| --- | --- |
| Cluster/capacity catalogue | Stable identity; site/cell; capacity role; actual hosts/control/storage components; accepted zone and co-residency profile; platform/version; management authority; service classes; rack/power/fabric dependencies; failure and maintenance basis; measured survivor capacity; reservations; native qualification references |
| WSD placement schedule | WSD/tenant owner; lifecycle environment; each domain/zone and its eligible primary/recovery pool; native network/policy identity; compute/storage/protection offer; shared-service bindings; capacity reservations; placement and anti-affinity constraints; permitted migrations; recovery/retention requirements |

Admission evaluates every bottleneck: surviving compute, storage/rebuild headroom, attachment and edge context slots, route/policy/session capacity, service throughput and recovery commitments. Do not derive a universal three-node minimum or a fixed cluster count from this role list. Product quorum, supported minima, failure tolerance, peak/rebuild load and maintenance requirements determine actual sizing.

## 9. Terraform and Ansible implementation work

| Backlog | Cluster-specific work to add to the existing package | Completion evidence |
| --- | --- | --- |
| W01 | Accept cluster roles, sharing/dedication, zone-management/storage realization and WSD placement schedules | Every WSD domain and dependency resolves to an accepted capacity/service offer |
| W03–W04 | Separate state, credentials and inventories by resource owner and actual scope | A WSD executor cannot change provider cluster membership, fabric or unrelated WSD resources |
| W05–W08 | Commission physical hosts/fabric, platform clusters, edge, trust and services; publish accepted capacity | Native health/isolation and required failure tests, recoverable management and current capacity |
| W09–W12 | Enforce eligible host/cluster/storage placement and bind WSD allocations to commissioned envelopes | Repeated WSD creation consumes capacity without silently commissioning a new cluster or editing IDs manually |
| W13–W15 | Configure guest/service bindings and permitted paths without weakening domain placement or ownership | Useful workloads and approved paths; denied cross-WSD and management paths |
| W16–W20 | Observe actual host/storage/control placement as well as logical resource state | Misplacement, partial enforcement or stale eligibility prevents activation |
| W21–W25 | Apply the same placement rules during maintenance, upgrade, HA, restore, migration and retirement | Tested recovery and cleanup preserve other WSDs and retained data; WSD deletion never destroys a shared provider cluster |

Provider commissioning and WSD allocation must remain distinct execution scopes. Terraform/Ansible can coordinate accepted handoffs, but the routine WSD workflow receives only the authority to allocate its eligible resources. Cluster growth, firmware/host lifecycle, shared-service retirement and destruction of provider foundations remain separately owned infrastructure changes.
