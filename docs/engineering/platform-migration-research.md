# Platform migration research: verified implementation decisions

Reviewed 28 September 2026 against `implementation/all-waves` at
`d2935a2cdc9fa114c2ed73251aa95379a34f9c5e`. This is an evidence and design record,
not a second roadmap. The [existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md)
remains the delivery authority. No installed vendor environment was contacted.

## Research corrections

The supplied research used approximate/nonexistent repository paths, proposed
renumbering the programme, and misidentified active qualification implementations
as obsolete. Those recommendations are rejected. Keep
`provisioner/qualification/{registry,native,provenance,target_selection,campaign}.py`
as the current owners. Their retired script entry points remain deleted. The
97 capability IDs already include SR-IOV, storage QoS, encryption, firewalling and
HA; do not add synonymous vendor-prefixed flags to inflate apparent coverage.

A vendor capability, selected deployment configuration, repository implementation,
local test, native qualification and current authority are different facts. No
product page, version threshold, fixture or feature name can supply the latter
five. Missing documentation is unverified, not a proof of permanent vendor
non-support. Missing observed facts are unknown, not false.

## Verified source decisions

All sources below were consulted on 28 September 2026. Public documentation
supports the stated assumption only; installed product/API/provider/driver,
entitlement and migration-tool versions still need an exact qualified tuple.
A `latest` documentation site may describe a development branch, not a release.

| Source | Supported fact and scope | Implemented interpretation / remaining qualification |
|---|---|---|
| [Broadcom NSX KB 442835](https://knowledge.broadcom.com/external/article/442835/cannot-add-tier0-vrf-gateway-to-a-tier0.html) | Tier-0 VRF cannot use an active-active **stateful** parent; active-standby and active-active stateless are distinct configurations. The public article does not give a complete version matrix. | The explicit selected VRF/parent combination is checked. A missing parent observation remains unknown. No automatic HA reconfiguration. Qualify exact topology under B18/B27/B47. |
| [Neutron networking concepts](https://docs.openstack.org/neutron/latest/admin/intro-os-networking.html), updated 2026-07-06 | Port security groups use additive allow rules; they are not ordered deny/allow policies. Disabling port security also disables the documented basic and anti-spoof controls. | Require enforcement state, all-selected-NIC coverage and rule model separately. A security group is not automatically equivalent to NSX/Flow policy. B27 still requires independent permitted-flow and denied-flow tests. |
| [Neutron SR-IOV guide](https://docs.openstack.org/neutron/latest/admin/config-sriov.html) | The documented direct SR-IOV datapath has security limitations. Migration behavior differs between indirect and direct interfaces; newer Nova supports conditional detach/reattach paths. | Record security path and migration mode separately. Do not impose a universal SR-IOV migration ban or claim transparent continuity. All-NIC firewall claims combined with an observed bypass are blocked. |
| [Open vSwitch DPDK guide, 2025.1](https://docs.openstack.org/neutron/2025.1/admin/config-ovs-dpdk.html) | The described vhost-user datapath needs huge pages and compatible host/guest components. | A selected OVS-DPDK datapath without configured huge-page evidence is unknown/blocked. This does not implement a DPDK provisioner or qualify NIC hardware. |
| [Cinder basic volume QoS](https://docs.openstack.org/cinder/latest/admin/basic-volume-qos.html), updated 2021-09-24 | Basic QoS describes ceilings, volume-type association and front/back-end consumption; ceilings do not guarantee a minimum IOPS service. | Distinct minimum/maximum properties and consumer scope. A maximum cannot fulfill a requested minimum; backend and load qualification remain B23/B25/B47. |
| [Neutron API v2](https://docs.openstack.org/api-ref/network/v2/index.html) | Port security, native binding types, group IDs, QoS-policy identity, fixed addresses and allowed address pairs are separate attributes. Extension visibility depends on deployment and authorization. | The project-scoped collector retains a bounded whitelist of those observed attributes. Omission remains unknown. It does not turn IDs or metadata into policy-equivalence evidence. |
| [Cinder API v3](https://docs.openstack.org/api-ref/block-storage/v3/index.html) | Volume encryption, multiattach and volume type are distinct from size. Encryption keys and attachment semantics require separate handling. | The collector records typed values without key material or arbitrary metadata. A multiattach flag is not clustered-filesystem safety or writer fencing. |
| [Nutanix Flow](https://www.nutanix.com/products/flow) | Flow Network Security provides distributed firewalling; Flow Virtual Networking provides networking/overlay functions. Monitor and enforce modes differ. | No AOS-version-only enablement and no assumption that FVN proves FNS. Explicit observed routing/security properties and independent policy tests are required. Product page evidence is not an installed API contract. |
| [Nutanix Move](https://www.nutanix.com/products/move) | Product documentation describes pre-seeding, final synchronization, shutdown and target boot. | Warm disk copy is not preserved running-memory state. No reverse route, arbitrary vTPM portability or exact source/target support is inferred from marketing. B38–B42 require the selected Move/converter support matrix and native campaign. |
| [Nova live migration configuration](https://docs.openstack.org/nova/latest/admin/configuring-migrations.html) | Native live migration has hypervisor, transport and storage prerequisites. | Same-platform relocation is not cross-hypervisor conversion. Mixed comparisons return a blocked destination instead of discarding other rows. B39 still owns native relocation implementation. |

Encryption layer equality in this increment is a conservative repository policy,
not a vendor limitation: changing guest/hypervisor/backend protection requires a
future explicit reviewed transformation rather than silent substitution. vTPM
state recreation likewise does not satisfy state preservation. Cross-ISA whole-VM
conversion is blocked by architecture mismatch; approved application rebuild is a
different strategy. These are implementation decisions derived from preservation
requirements, not unsupported universal vendor statements.

## Implemented data path

`provisioner/domain/capability_properties.py` owns the typed property vocabulary,
closed values, `eq`/`gte`/`lte` operators, bounded immutable requirements,
intersection, implication and deterministic unknown/mismatch results. Its digest
pins the interpretation. There are 28 properties beneath the existing 97 IDs.

Profile catalogues now accept `requires.constraints`. Each property must name an
existing required capability owner; unknown keys, duplicate requirements and
contradictory selected profiles are rejected. Security profiles require independent
routing and enforced deny-default gateway policy; profiles using distributed
firewalling also require enforcement across all selected workload NICs. Compute
profiles explicitly require x86_64. Deferred encryption remains deferred and adds
an explicit destination-key readiness obligation.

For example, a reviewed workload profile can express a minimum separately from
an unrelated ceiling:

```json
{
  "capabilities": ["storage_qos"],
  "constraints": [
    {"property": "storage_qos.minimum_iops", "operator": "gte", "value": 1000}
  ]
}
```

Profile resolution is format 3. Planning carries the complete constraint set into
per-cluster placement; another cluster or a cell-wide flag cannot fill a selected
cluster's missing observations. Inventory properties are immutable copies and
remain bound by the existing inventory/plan digests. Synthetic reference inventory
explicitly supplies test facts and remains `FIXTURE_NOT_AUTHORITATIVE`; all compiled
examples remain disabled. A schema/catalogue change needs a newly reviewed plan.

Portable policy capsule/realization format 2 retains the source constraints and
requires the destination plan to enforce them or stronger compatible bounds.
It rejects old capsules, property-digest mismatch, incompatible requirements and
weaker destination profiles. It never copies native rule IDs or silently replaces
mandatory controls.

The discovery normalizer is `hosting-assessment-normalizer/2`. Source observations
carry `requiredCapabilities`, `capabilityRequirements` and
`capabilityPropertySchemaDigest`; selected target pools carry `observedCapabilities`,
`capabilityProperties` and the same interpretation digest. Unknown/malformed or
superseded properties cannot be restamped as current. Existing signed control
findings must bind both raw and normalized snapshots and the current normalizer;
old signed reviews are rejected, not reinterpreted. A complete-looking set is
still subject to independent route, policy, security and recovery review.

Whole-VM comparison requires actual source architecture, firmware, secure-boot,
vTPM, encryption, shared-disk and passthrough facts, plus an application-reviewed
memory-state requirement. Encryption needs the observed layer and destination key
readiness; shared disks and passthrough need qualified writer/device mappings.
Conversion needs verified destination guest drivers. Warm transfer additionally
requires bounded measured dirty-rate and throughput samples and blocks a
nonconvergent observed rate. These checks neither predict total downtime nor
implement data transfer. Comparisons always keep `executionAuthorized` false.

The OpenStack collector uses existing exact-project GET routes. Its new fields
are observations, not capability-property assertions: no arbitrary VM metadata,
user data, connection passwords or encryption keys are ingested. Address and group
sets are bounded, malformed/duplicate identities rejected, and explicit false,
empty and null values distinguished from omission. No missing privileged binding
field is filled from the platform family.

## Completion and remaining work

Tests exercise property ownership/types, profile intersections, stronger/weaker
constraints, scoped placement, old schema rejection, native contradictions,
vTPM/encryption/hardware gaps, convergence, two-destination isolation, normalization,
real signature rejection, and bounded OpenStack response parsing. Existing golden
examples were regenerated for the changed digests, not granted execution authority.

The implementation is a schema/policy/discovery increment of B03/B14–B19/B25–B27,
with B38–B42 comparison prerequisites. It does not finish B05, collector credential
and profile wiring, native rule generation, admitted provisioning, image conversion,
transfer workers, fencing, final sync, cutover, post-write recovery or B47–B50.
The [wave-plan acceptance expansion](../product/enterprise-workload-mobility-execution-plan.md#8-research-driven-acceptance-and-implementation-delta)
allocates those obligations without new B identifiers. Native qualification remains
unselected; production mutation is neither enabled nor attempted.
