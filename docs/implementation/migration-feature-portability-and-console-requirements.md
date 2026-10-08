# Migration feature portability and mandatory Console evidence

**Source of truth:** [`migration-feature-policy-v1.json`](../../contracts/capabilities/migration-feature-policy-v1.json), tied to the [field crosswalk](migration-field-crosswalk.md) and [collection manifest](migration-collection-manifest.md).

This defines **30 feature areas**, **27 operator/independent evidence obligations** and candidate coverage across all **nine** VMware/AHV/OpenStack source-destination combinations. It is a **declarative E2 policy**, not a claim that any installed API, feature or native migration is qualified. Every direction remains **unknown** until exact API-version/entitlement evidence, native E3 behavior and independent E4 receiving acceptance exist.

## What actually maps across platforms

- **Data representations can map**: source power-state vocabulary, total vCPU count, RAM in MiB and MAC identity format. Their *values* can be normalized. Do not infer that the destination will run the VM without changing drivers, network placement and guest topology. All changes require source freshness and post-conversion readback.
- **Platform adaptations are needed**: disk/image capture/import, controller/boot models, firmware/Secure Boot/vTPM, shared and encrypted storage, target VM creation, network attachment, network security and monitoring. These are transformations with independently qualified implementations, not field copies.
- **Administrator-owned decisions are mandatory**: application datasets and consistency, dependencies, writer fencing, accepted data loss/outage, target placement/network intent, required policy flow outcomes, measured recovery, key custody, service integration and retention. Some are expressed via existing per-VM review inputs, others via the operator-readiness form. Reference entry does not establish validity.
- **No established generic equivalent**: special hardware (GPU/PCI passthrough), unmatched source fields, provider-specific metadata and capabilities that a destination API/version does not expose. The correct decision is **unknown/blocked for critical requirements** until a qualified alternative is demonstrated; optional only if a reviewer proves it has no functional/security impact and the operation is suppressed.
- **Optional classification is conditional**: labels/descriptions, genuinely nonessential categories and QoS settings and redundant policy rules may be omitted only with E4-reviewed effect suppression. A mandatory rate limit, security group rule, segmentation policy or application dependency is never downgraded just because the same API field is missing on the target.

## Feature-level mapping contract

Legend: **Normalize** = data-level conversion candidate with readback; **Adapter** = native operation needs qualified implementation; **Owner + native** = owner input and independent native validation; **Optional/E4** = may be omitted only under verified nonessential conditions.

| Feature | Mapping treatment | Criticality | Source / target field coverage | Operator obligation |
| --- | --- | --- | --- | --- |
| `platform.api` — API releases and entitlement | Version-qualified | **critical** | vmware: 4 source / 1 target; ahv: 4 source / 2 target; openstack: 4 source / 3 target | Native data and/or independent adapter only |
| `vm.identity` — VM identity and source scope | Qualified adapter | **critical** | vmware: 6 source / 0 target; ahv: 7 source / 0 target; openstack: 3 source / 0 target | Native data and/or independent adapter only |
| `vm.power` — Power state and fencing | Representational normalization + recheck | **critical** | vmware: 1 source / 0 target; ahv: 1 source / 0 target; openstack: 1 source / 0 target | Native data and/or independent adapter only |
| `vm.compute` — vCPU, RAM, CPU topology | Representational normalization + recheck | **critical** | vmware: 5 source / 1 target; ahv: 4 source / 0 target; openstack: 3 source / 1 target | Native data and/or independent adapter only |
| `vm.placement` — Host/cluster placement, capacity, quota | Owner + native qualification | **critical** | vmware: 0 source / 4 target; ahv: 0 source / 2 target; openstack: 1 source / 2 target | 1 named owner/independent requirement(s) |
| `guest.firmware` — Firmware, Secure Boot, vTPM | Qualified adapter | **critical** | vmware: 3 source / 0 target; ahv: 3 source / 0 target; openstack: 1 source / 0 target | Native data and/or independent adapter only |
| `guest.drivers` — Guest OS, agents, activation, drivers | Owner + native qualification | **critical** | vmware: 3 source / 1 target; ahv: 2 source / 1 target; openstack: 5 source / 1 target | 2 named owner/independent requirement(s) |
| `guest.devices` — GPU/PCI and removable devices | Qualified adapter | **critical** | vmware: 1 source / 0 target; ahv: 2 source / 0 target; openstack: 0 source / 0 target | Native data and/or independent adapter only |
| `storage.disks` — Complete root, local and attached disks | Qualified adapter | **critical** | vmware: 9 source / 0 target; ahv: 5 source / 0 target; openstack: 9 source / 0 target | Native data and/or independent adapter only |
| `storage.controller` — Disk controllers and boot ordering | Qualified adapter | **critical** | vmware: 1 source / 0 target; ahv: 2 source / 0 target; openstack: 1 source / 0 target | Native data and/or independent adapter only |
| `storage.sharing` — Shared disks and multiwriter semantics | Owner + native qualification | **critical** | vmware: 1 source / 0 target; ahv: 1 source / 0 target; openstack: 2 source / 0 target | Native data and/or independent adapter only |
| `storage.encryption` — Storage encryption and key custody | Owner + native qualification | **critical** | vmware: 1 source / 0 target; ahv: 1 source / 0 target; openstack: 1 source / 1 target | 1 named owner/independent requirement(s) |
| `storage.target` — Destination storage backend and capacity | Qualified adapter | **critical** | vmware: 0 source / 2 target; ahv: 0 source / 4 target; openstack: 0 source / 5 target | Native data and/or independent adapter only |
| `storage.transfer` — Capture, image conversion, import and VM creation | Qualified adapter | **critical** | vmware: 2 source / 1 target; ahv: 1 source / 2 target; openstack: 2 source / 3 target | Native data and/or independent adapter only |
| `network.nics` — NIC count, MAC address and hardware | Qualified adapter | **critical** | vmware: 3 source / 0 target; ahv: 3 source / 0 target; openstack: 4 source / 0 target | Native data and/or independent adapter only |
| `network.routing` — IPAM, DNS, segments and routing | Owner + native qualification | **critical** | vmware: 1 source / 1 target; ahv: 2 source / 5 target; openstack: 5 source / 6 target | 2 named owner/independent requirement(s) |
| `network.flows` — Required connectivity and link state | Owner + native qualification | **critical** | vmware: 2 source / 0 target; ahv: 1 source / 0 target; openstack: 1 source / 0 target | 1 named owner/independent requirement(s) |
| `network.security` — Firewall, microsegmentation and isolation | Owner + native qualification | **critical** | vmware: 0 source / 2 target; ahv: 0 source / 2 target; openstack: 3 source / 3 target | 3 named owner/independent requirement(s) |
| `security.scope` — RBAC, tenants, licenses and credentials | Owner + native qualification | **critical** | vmware: 0 source / 1 target; ahv: 0 source / 2 target; openstack: 0 source / 2 target | 1 named owner/independent requirement(s) |
| `app.datasets` — Dataset coverage and mounts | Operator input + independent qualification | **critical** | vmware: 0 source / 0 target; ahv: 0 source / 0 target; openstack: 0 source / 0 target | 1 named owner/independent requirement(s) |
| `app.consistency` — Application consistency and quiescence | Operator input + independent qualification | **critical** | vmware: 0 source / 0 target; ahv: 0 source / 0 target; openstack: 0 source / 0 target | 1 named owner/independent requirement(s) |
| `app.dependencies` — External service and application dependencies | Operator input + independent qualification | **critical** | vmware: 0 source / 0 target; ahv: 0 source / 0 target; openstack: 0 source / 0 target | 1 named owner/independent requirement(s) |
| `app.objectives` — Maximum outage and data loss | Operator input + independent qualification | **critical** | vmware: 0 source / 0 target; ahv: 0 source / 0 target; openstack: 0 source / 0 target | 2 named owner/independent requirement(s) |
| `app.validation` — Post-migration application behavior | Operator input + independent qualification | **critical** | vmware: 0 source / 0 target; ahv: 0 source / 0 target; openstack: 0 source / 0 target | 1 named owner/independent requirement(s) |
| `cutover.writer` — Final synchronization and writer fencing | Operator input + independent qualification | **critical** | vmware: 0 source / 0 target; ahv: 0 source / 0 target; openstack: 0 source / 0 target | 2 named owner/independent requirement(s) |
| `recovery.restore` — Backup, restore and rollback | Operator input + independent qualification | **critical** | vmware: 0 source / 0 target; ahv: 0 source / 0 target; openstack: 0 source / 0 target | 3 named owner/independent requirement(s) |
| `recovery.retention` — Retention, cleanup and source retirement | Operator input + independent qualification | **critical** | vmware: 0 source / 0 target; ahv: 0 source / 0 target; openstack: 0 source / 0 target | 1 named owner/independent requirement(s) |
| `operations.service` — Time, identity, logging, monitoring, backup | Operator input + independent qualification | **critical** | vmware: 0 source / 0 target; ahv: 0 source / 0 target; openstack: 0 source / 0 target | 2 named owner/independent requirement(s) |
| `metadata.optional` — Nonessential labels, tags and conveniences | Optional only with E4 suppression | **optional** | vmware: 1 source / 1 target; ahv: 2 source / 1 target; openstack: 1 source / 0 target | 2 named owner/independent requirement(s) |
| `network.qos` — Nonessential network QoS and bandwidth settings | Optional only with E4 suppression | **optional** | vmware: 0 source / 0 target; ahv: 0 source / 0 target; openstack: 1 source / 1 target | Native data and/or independent adapter only |

The counts show **how many source fields are mapped in the version-controlled
collection manifest**, not actual values, support on any installed API,
feature completeness, or a qualified migration route.

## All nine directed migration candidates

Every row is a mapping *proposal*, not a supported or unsupported conclusion.

| Direction | Normalize + recheck | Qualified adapter | Owner + native verification | Missing direct field, qualified alternative required | Nonessential optional/E4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| vmware → vmware | 2 | 14 | 9 | 4 | 1 |
| vmware → ahv | 1 | 14 | 9 | 5 | 1 |
| vmware → openstack | 2 | 15 | 9 | 4 | 0 |
| ahv → vmware | 2 | 14 | 9 | 4 | 1 |
| ahv → ahv | 1 | 14 | 9 | 5 | 1 |
| ahv → openstack | 2 | 15 | 9 | 4 | 0 |
| openstack → vmware | 2 | 15 | 9 | 3 | 1 |
| openstack → ahv | 1 | 15 | 9 | 4 | 1 |
| openstack → openstack | 2 | 16 | 9 | 2 | 1 |

The existence of a mapping is not permission for Lifecycle to perform a
native write. Each migration must determine exact *used* capabilities,
destination API/version and entitlement, qualification expiry, adapter
equivalence, permitted omissions and current owner observations. Any
unverified **critical** capability fails closed.

## Exact Console responsibilities

**Per-VM migration review** (existing fields) accepts explicit datasets,
application facts, objectives and destination mappings. **Operator readiness**
accepts named references to approved scope, accounts, services, backup,
recovery, trust, network and measured capacity. **Independent proof** comes
from Assurance or operating reviewers; do not enter secret values or
substitute manually typed native facts.

| Owner/assurance requirement | Severity | Applies | Migration review field | Operator readiness field | Verification owner |
| --- | --- | --- | --- | --- | --- |
| `application.consistency` | critical | `always` | `owner_inputs.application_consistency` | `consistency_ref` | Application/platform owner |
| `application.datasets` | critical | `always` | `datasets` | `consistency_ref` | Application/platform owner |
| `application.dependencies` | critical | `always` | `owner_inputs.dependencies` | `service_protocol_ref` | Application/platform owner |
| `application.writer_fencing` | critical | `cutover` | `owner_inputs.writer_fencing` | `writer_fencing_ref` | Application/platform owner |
| `application.final_delta` | critical | `when:delta_method` | `owner_inputs.delta_protocol` | `delta_ref` | Application/platform owner |
| `application.outage_objective` | critical | `always` | `objectives.max_outage_seconds` | `max_outage_seconds` | Application/platform owner |
| `application.data_loss_objective` | critical | `always` | `objectives.max_data_loss_bytes` | `max_data_loss_bytes` | Application/platform owner |
| `guest.boot_drivers` | critical | `always` | `owner_inputs.guest_transformation_profile` | `guest_recipe_ref` | Application/platform owner |
| `guest.os_activation` | critical | `when:license_bound` | `owner_inputs.guest_transformation_profile` | `guest_recipe_ref` | Application/platform owner |
| `guest.application_health` | critical | `cutover` | `owner_inputs.service_and_policy_validation` | `traffic_ref` | Independent witness/reviewer |
| `storage.encryption_key_custody` | critical | `when:encrypted` | — | `custody_ref` | Independent witness/reviewer |
| `recovery.rollback_protocol` | critical | `always` | `owner_inputs.recovery_protocol` | `recovery_ref` | Application/platform owner |
| `recovery.restore_evidence` | critical | `always` | — | `restore_ref` | Independent witness/reviewer |
| `network.required_paths` | critical | `always` | `owner_inputs.service_and_policy_validation` | `traffic_ref` | Independent witness/reviewer |
| `network.address_ownership` | critical | `always` | — | `reservation_ref` | Application/platform owner |
| `network.firewall_flows` | critical | `when:required_security_policy` | `owner_inputs.service_and_policy_validation` | `traffic_ref` | Independent witness/reviewer |
| `security.tenant_isolation` | critical | `always` | — | `traffic_ref` | Independent witness/reviewer |
| `security.credential_scope` | critical | `always` | — | `account_scope_ref` | Application/platform owner |
| `operations.backup_coverage` | critical | `always` | — | `restore_ref` | Independent witness/reviewer |
| `operations.monitoring` | critical | `always` | — | `service_protocol_ref` | Independent witness/reviewer |
| `operations.dns_cutover` | critical | `cutover` | — | `traffic_ref` | Application/platform owner |
| `operations.time_and_identity` | critical | `always` | — | `service_protocol_ref` | Application/platform owner |
| `operations.cleanup_and_retention` | critical | `always` | `owner_inputs.retention_and_cleanup` | `retention_ref` | Application/platform owner |
| `application.optional_tags` | optional | `when:present` | — | No current field; E4 omission workflow needed | Independent E4 omission approval |
| `network.optional_firewall_flows` | optional | `when:approved_nonessential` | — | No current field; E4 omission workflow needed | Independent E4 omission approval |
| `operations.optional_integrations` | optional | `when:present` | — | No current field; E4 omission workflow needed | Independent E4 omission approval |
| `placement.native_reserved_capacity` | critical | `always` | — | `reservation_ref` | Independent witness/reviewer |

### Mandatory versus conditional

An `always` critical requirement is mandatory for every selected migration.
A `cutover` critical requirement is mandatory before its cutover effect.
A `when:...` critical requirement becomes mandatory whenever its condition
holds; an **unknown condition is not a false condition** and therefore
cannot silently remove the requirement. Examples:

- **Every migration:** discover and recheck all boot/data disks, power,
  CPU/RAM, source identity, installed API versions, destination
  provisioning/placement/capacity, required allow/deny network behavior,
  guest boot/drivers, owner datasets/dependencies, approved objectives,
  backup/rollback, service validation and security isolation.
- **Encrypted or vTPM-bearing workload:** verify key custody, encryption
  compatibility, export/import procedure and device support, or block.
- **Shared disk / multiwriter:** qualified consistency and writer fencing,
  or block. An OpenStack Cinder multiattach flag is not analogous to a
  VMware disk sharing mode.
- **Delta migration:** final synchronization record is required; cold
  export does not need an invented delta protocol. The application
  writer-fencing obligation remains.
- **Optional nonfunctional fields:** a reviewer must prove nonessential
  impact and bind E4 omission to the exact disabled native effect. No
  default approve or empty acknowledgments.

### What is enforced now and what remains open

**Implemented and source-tested:** Inventory owns the source profile and
destination facts, validates eight per-VM `owner_inputs` references
(`delta_protocol` conditional for cold export), validates the exact
dataset-to-disk map and owner objectives, and prevents operators
from overwriting native disk/CPU/firmware/network observations. The
Console displays proposed per-direction feature treatment, read-only
native source information, outstanding mandatory review fields, and a
link to the separate operator-readiness form.

**Not yet implemented/qualified:** a single authoritative feature-aware
readiness evaluator joining each VM's exact profile/review, site-level
operator evidence and independently signed E3/E4 observations; conditional
applicability detection for all security, encryption, special-device and
license states; persisted operator acceptance of optional effects with
real suppression witnesses; dynamically populated current API
compatibility; and final Plan/Lifecycle effect admission on these
requirements. The Console shows such obligations as **unverified**,
even when a text reference is supplied. Follow `next_work.md`
CT-N15/CT-N16 and the new CT-N17 backlog.

## Validation

`scripts/assurance/test_migration_feature_policy.py` verifies that all
**116** canonical crosswalk groups belong to exactly one feature, all **27**
owner attributes match their criticality/conditionality/source schema and
existing Console field identifiers, all nine directions bind the correct
source/target fields without inheriting support, and the Console's
consumer projection equals the authoritative JSON byte-for-byte.
Additional Inventory domain tests reject missing owner fields, data
coverage and invalid accepted objectives. The capability-assurance CI
workflow executes the static validations; **hosted CI results must still
be checked against the current PR head**.
