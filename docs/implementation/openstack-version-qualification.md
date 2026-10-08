# OpenStack versions and API qualification

Owner: Inventory and native platform integration owners. Reviewed: 2026-10-06.
This is the version/capability register for the existing ADR-015 baseline.
Documentation review, API observation, administrator validation and native operation
qualification are distinct evidence. No release currently has an E3-qualified native
adapter/operation tuple in this repository.

## Versions, newest first

| Release | Released | Nova documented microversion ceiling | Documentation scope | Native tuple qualification |
| --- | --- | --- | --- | --- |
| 2026.2 Hibiscus | 2026-09-30 | 2.104 | Current released baseline; API contracts reviewed | Not qualified; connected Q05/Q06 evidence required |
| 2026.1 Gazpacho (SLURP) | 2026-04-01 | 2.103 | Prior released baseline; Compute differences reviewed | Not qualified |
| 2025.2 Flamingo | 2025-10-01 | 2.100 | Listed compatibility candidate; full service review pending | Not qualified |
| 2025.1 Epoxy (SLURP) | 2025-04-02 | 2.100 | Listed compatibility candidate; full service review pending | Not qualified |

The [official release index](https://releases.openstack.org/) identifies Hibiscus
as the latest maintained release and 2027.1 Indri as development. A distribution's
support policy and installed packages remain deployment-specific. This list is not
an upgrade recommendation. The [Hibiscus Compute history](https://docs.openstack.org/nova/2026.2/reference/api-microversion-history.html)
and [Gazpacho history](https://docs.openstack.org/nova/2026.1/reference/api-microversion-history.html)
provide the ceilings above. Version 2.104 adds availability-zone pinning updates;
2.103 removes the old `os-volumes_boot` alias. The collector's existing resource
reads still request Compute 2.1 and Volume 3.0 explicitly. Discovery ceilings do
not silently change request microversions or authorize newer operations.

## API and capability boundaries

| Service | Documented API baseline | Pull / implementation assessment |
| --- | --- | --- |
| Keystone | [Identity v3](https://docs.openstack.org/api-ref/identity/v3/) | Scoped service catalog; registered services are advertised, not proven usable. Catalog addresses never extend trusted outbound destinations. Project application credentials can restrict roles/access rules. |
| Nova | [Compute v2.1](https://docs.openstack.org/api-ref/compute/) with explicit microversions | Version range, flavors and availability zones; workload drivers, NUMA/PCI and live migration need additional backend-specific qualification. |
| Neutron | [Networking v2.0](https://docs.openstack.org/api-ref/network/v2/) with extensions | Extension aliases plus configured subnets, ports/bindings, routers, security group rules, trunks and QoS policies. Driver, project permissions and actual configuration determine usability. |
| Cinder | [Block Storage v3](https://docs.openstack.org/api-ref/block-storage/v3/) with microversions | Version range and visible volume types. The published [microversion history](https://docs.openstack.org/api-ref/block-storage/api_microversion_history.html) currently ends at 3.71 with an older release label; live version discovery remains authoritative for installed bounds. Snapshot, backup, encryption, replication and multiattach require their specific backend/operation checks. |
| Glance | [Image v2](https://docs.openstack.org/api-ref/image/v2/) | Version discovery, available import methods and stores through separately trusted service streams. Import and conversion still require guest/format/driver checks. |
| Placement | [Placement 1.x](https://docs.openstack.org/placement/2026.2/placement-api-microversion-history.html) | Published history reaches 1.39; pull installed bounds and traits. Traits alone prove neither available capacity nor a reservation. |
| Optional services | [2026.2 API directory](https://docs.openstack.org/2026.2/api/index.html) | Catalog detects Octavia, Designate, Barbican, Manila, Swift and Heat registrations. Their resource configuration and native operations require dedicated adapters; presence is not a qualified equivalent. |

A missing extension, permission denial, incomplete list, absent service stream or
unsupported response stays unknown/not observed. It does not establish absence
of the software from the installation. Standard APIs do not reliably expose the
distribution/package release, support entitlement or every backend build; Console
manual references cover those facts and workload/business requirements.

## Console and owner API

Open Inventory → approved site → **Configure porting**. Select source and destination,
save, and use **Pull source configuration** / **Pull destination configuration**.
Core Nova/Neutron/Cinder queries derive from already trusted enrolled service bases.
Each query consumes its own existing worker lease and rate budget. No administrator
needs to type API versions or extension flags. Inventory stores bounded API projections
with endpoint, generation, observation time, expiry and content identity.

Review configured versus advertised findings, select required capabilities, and
use an attributed include/exclude interpretation only with a reason/evidence reference.
API observations and API version bounds are immutable. An interpretation cannot
override authentication, scope, expiry, native support qualification or execution
holds. Manual fields capture distribution/support evidence and ownership, network,
guest/service mapping, automation, recovery, activation, retirement and campaign
references; credentials remain in the existing protected connection system.

Save and confirm the exact revision. A new API generation, expiry, policy change,
revocation or edited input invalidates current confirmation. Confirmation records
who acknowledged the findings and disclosed gaps; it is not a native support grant.
Planning's existing qualified-capability admission remains unchanged and held.

Inventory owns `GET/POST .../sites/{site}/porting-configuration`,
`POST .../porting-configuration/confirmations`, and admin-only
`POST .../endpoints/{endpoint}/configuration-pulls`. Every request uses current
Governance delegation. Writes use existing command receipts, revision preconditions,
audit and outbox transactions. Console stores no sibling service data directly.

Optional protected streams use `kind: config_image_versions`, `config_image_import`,
`config_image_stores`, `config_identity_catalog`, `config_placement_versions` or
`config_placement_traits`, and `api_version: discovery-v1`. Use an unversioned service
base for version discovery, Image `/v2` for import/stores, Identity `/v3` for catalog,
and the Placement service base for traits. Existing address pins, CA and credential
mounts apply. An explicit core configuration stream can select a nonstandard trusted
service prefix; it never takes a URL from a browser request or native response.

The first configuration projection is bounded to fewer than 100 items per query,
128 KiB per projection and the existing generation/page budgets. A continuation or
bound hit is held as an invalid/incomplete response, never truncated into a complete
capability claim. The Console shows up to five examples with the full stored count.
Large installations need a subsequent bounded pagination expansion. VMware retains
its existing resource discovery; VMware/AHV feature configuration is not claimed
as implemented by this OpenStack increment.
