# P07 native provisioning implementation

Scope: P07.01–P07.06; R07/R08/R16–R21/R25/R29–R31/R33.

[ADR-016](../decisions/adr-016-native-api-plans-and-resource-ownership.md) defines
native API-only provisioning. Planning binds exact native resource specifications,
API/adapter artifacts, scope, field ownership and custody generations to the
immutable approved plan. The [P07 work packages](phases/p07.md) and
[G07](gates.md#g07--native-openstack-provisioning) retain their native acceptance scope.

## Implemented boundaries

- API-first Inventory/Console configuration and bounded fifteen-input commissioning
  checks, exact packet/artifact binding and independent observation metadata.
- Closed native operation plans for quarantined Neutron ports, Cinder image-backed
  volumes and Nova servers, with exact disk/NIC mapping and no runtime-generated intent.
- Scoped writer authentication, pinned-address verified TLS, per-request current
  authority, durable submission/acceptance journals and bounded native status polling.
- Independent exact-ID readback using a separate identity, including attachments,
  boot images, placement, ownership and quarantine/security fields.
- Worker-owned PostgreSQL attempt/custody claims that survive duplicates, response
  loss and restart. Unknown effects cannot be blindly repeated or auto-released.
- Lifecycle single-use stage grants, durable native Temporal outbox and distinct
  queue, single-attempt stages, cancellation holds, internal worker/boundary TLS,
  independent readiness conditions and separate retention/retirement controls.

The [adapter runbook](../operations/runbooks/openstack-native-adapters.md),
[commissioning runbook](../operations/runbooks/openstack-commissioning.md) and
[workflow control](../operations/runbooks/native-workflow-control.md) describe the
current contracts. No Terraform executable, provider, module, state compatibility
layer or alternate execution path is required.

## Qualification and remaining native work

The [native API qualification index](../../verification/p07/native-api/qualification-index.json)
binds 276 Lifecycle and 139 worker tests without skips, 93 preparation tests and
43 Temporal checks with six replayed histories to source `4ee67fdd`. Original
failures and corrections remain retained. Synthetic HTTP responses establish
component behavior only. The
[completion packet](p07-completion-review.md) lists the missing commissioned owner,
guest/service/traffic/retirement integrations and actual Q05/Q06 observations.
API requests cannot prove immediate provider-side cancellation or stale-worker
exclusion; independently observed provider quiescence is required before advancement.

No installed OpenStack environment, actual Q05/Q06 campaign, service-owner receipts
or G07 receiving decision has been supplied. Those outcomes must remain unclaimed.
Native platform support and completion are recorded only from actual observations
in the canonical delivery register.

Migration is [P08](p08-native-migration.md). ExportVm/NFC, isolated clone capture,
copy-only conversion/guest transformation and delta cutover do not expand P07.
