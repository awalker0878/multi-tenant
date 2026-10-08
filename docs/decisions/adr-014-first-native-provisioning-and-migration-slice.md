# ADR-014 — First native provisioning and migration slice

Owner role: Product/infrastructure leads. Related phases: P00, P07, P08.

Origin: `DESIGN`. Disposition: `ACCEPTED` in the [decision register](decision-register.md).

## Context

The first native provisioning path is OpenStack. Migration is P08 and uses
native source/target APIs with minimal production-source changes. Exact installed
platform, guest, data and service tuples require independent qualification.

## Decision and scope

Use the [P08 native migration architecture](../implementation/p08-native-migration.md).
Inventory discovers source workload and destination capability profiles; Planning
binds one explicit method, source/destination identities, exact disk/resource maps,
conversion/transformation artifacts, acceptance checks, recovery boundaries and
authorization epoch to an immutable plan.

`ExportVm`/`HttpNfcLease` is the baseline generic VMware whole-VM export mechanism.
Capture a consistent disk-only snapshot and an isolated powered-off migration clone
bound to that snapshot. Export the clone through leased HTTPS URLs and verify the
native manifest. Native destination APIs import the planned disk format and create
the quarantined VM. Conversion and guest driver/tool changes operate only on the
migration/destination copy. Production source changes are limited to the explicitly
authorized consistency, power, snapshot and fencing operations.

Application rebuild/restore, snapshot baseline plus application delta, snapshot
baseline plus file delta, and cold export are distinct qualification scopes.
Planning selects one from demonstrated requirements and capabilities; execution
never switches to another after a failure. Low downtime requires a qualified delta
method. Without one, the source stays stopped/fenced for the authoritative cold
export and cutover. Optional external block replication requires its own approved,
entitled integration. VDDK is never required by the baseline product.

Terraform is not an execution dependency. Native APIs govern source and target
resources; immutable request plans, resource ownership, custody generations and
single-use authority follow [ADR-016](adr-016-native-api-plans-and-resource-ownership.md).

## Safety and qualification

Persist each effect before submission, retain native task/lease/object identities,
and hold unknown results without blind retry. Verify source and clone identity,
production-network disconnection, byte/disk completeness, encryption and trust.
An export lease does not fence production after completion. Independently verify
source-writer exclusion before target writes and preserve that fence through cutover.

Boot and validate the target in quarantine. Require all data, application, service,
backup and allowed/denied policy checks before activation. Before target writes,
source return requires a fenced target; after possible target writes, require an
explicit data-preserving recovery decision. Source retirement is separate authority.

Q05/Q06 qualify P07 provisioning; Q07/G08 qualify the selected migration method and
installed route. Synthetic tests do not establish native platform support. VMware →
Nutanix and VMware → VMware require separate destination adapters and qualification.

## Primary API references

- [VMware VirtualMachine operations](https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/vim.VirtualMachine.html)
- [VMware HttpNfcLease](https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/vim.HttpNfcLease.html)
- [OpenStack Image Service v2](https://docs.openstack.org/api-ref/image/v2/)
- [OpenStack Compute API](https://docs.openstack.org/api-ref/compute/)

## Revisit conditions

Installed APIs, capture/clone isolation, conversion compatibility, guest prerequisites,
delta semantics, source fencing or accepted outage/data boundaries change.
