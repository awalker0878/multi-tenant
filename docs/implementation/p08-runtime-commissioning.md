# P08 native worker and account commissioning

The native worker now has an executable composition entry point. It loads protected,
immutable operation artifacts, verifies their complete scope and custody binding,
and resolves only the explicitly selected installed adapter. Configuration is read
again during an effect; rotation, removal, expiry or changed artifact bytes hold
the operation. No registry entry can select a simulation adapter or a Python import.

This supplies a product runtime, not actual source/target accounts or a qualified
native migration. Planning can now compose complete immutable proposals. Lifecycle
native-owner integration and the selected application/guest/service implementation
are still required. P08/G08 remain
open until their original obligations are met.

## Complete Planning proposals and bulk Console

The new `planning-migration-v1.1` contract retains preparation and adds scoped
`migration-plan-options` and `migration-plans` POST operations. Both re-read the
confirmed Inventory review. Options expose only currently composable choices for
the requesting actor's tenant/application/environment/site and exact source/target
identities. The Console obtains disk mappings from the current saved group on the
server. It never accepts native intent bytes, credentials or throughput assertions
from the browser.

Mount `PLANNING_MIGRATION_RECIPES_FILE` as a protected absolute JSON file. Its exact
top-level shape is `schema_version: 1` and `recipes`, with up to 256 `{id, recipe}`
entries. Each recipe contains these fields:

| Field | Binding |
| --- | --- |
| `schema_version`, `scope` | Version 1 and tenant/site/environment/resource/project IDs |
| `base_content_sha256` | Current qualified operational `application.migrate` base plan |
| `source_identity_sha256`, `target_identity_sha256` | Exact current native profile identities |
| `mode`, `method`, `expires_at` | One explicit mode/method and commissioning expiry |
| `delta` | Method-matched kind, live-guest requirement and qualification digest |
| `artifacts` | Capture, transfer, conversion, guest, delta and recovery digests |
| `rehearsal_sha256`, `recovery_of_sha256`, `source_job_id` | Required cutover/recovery lineage, null when inapplicable |
| `intents` | Exact complete ordered stage set with distinct immutable digests |
| `native` | Configuration revision/digest, tuple/source revision, custody/ownership and complete allowed/denied policy cases |
| `campaign` | Route digest, six phase sizes and explicit shared resource demands |

Expiry cannot exceed the base plan, current facts or either profile. All disks and
datasets retain their current Inventory bindings. Data-phase size budgets must
cover the full virtual disk capacity. Budgets are not measured throughput evidence.
Recipes cannot extend authority or recompose an already composed plan.

Plan creation uses the existing immutable PostgreSQL record/outbox transaction and
actor-scoped idempotency. A lost response is retried unchanged. Later user validity
reads recheck the recipe and current Inventory inputs. Recipe changes or revocation
hold the proposal. `planning-v1.1` adds the complete composition and campaign fields;
published v1 contracts remain unchanged.

The Console uses migration v1.2 to preserve an explicit HTTP 423 commissioning hold
as a definite rejection. Such a response lets the user refresh plan choices; only
an uncertain outcome retains the unchanged retry command. The v1.1 bytes are retained.

For a saved fleet group, use **Find plan choices**, select the mode for each VM, and
**Create selected plans**. Each successful member links to Planning review and
independent approval. Held members keep their reasons. An uncertain reply retains
the same command and prevents changing its selection until resolved. No matching
choice means a current commissioned recipe/base plan is missing. Creation does not
start a migration or provide a native approval.

Lifecycle now serializes migration custody by native source VM identity, so different
VMs in one application can be admitted independently when their custody is distinct.
The same source VM cannot evade that hold by changing applications or destination
projects. Application-wide provision/retire holds still conflict. Existing retained
application-keyed jobs remain visible and recoverable across the upgrade.

The native owner port still needs real Governance/Inventory/custody reads and a
commissioned execution-plan resolver. The simulation approval endpoint remains
unsuitable for this purpose. This increment supplies proposal construction and worker
composition; it does not establish the missing end-to-end native authority path.

## Worker process

Run `lifecycle-worker-native --config /run/migration/worker.json`. The process serves
the existing `/internal/native-effects` contract over verified server TLS. It uses
the separately configured worker-owned PostgreSQL connection and existing native
migrations. Its credentials must have only the native journal runtime permissions.
No database migration or platform mutation occurs during startup.

The version 1 worker document has exactly `schema_version`, `callers_file`,
`registry_file`, `authority`, `tls_cert_file` and `tls_key_file`. Files are absolute,
bounded, non-symlink, regular protected mounts. `authority` has `base_url`, `address`,
`ca_file` and `token_file`, for the authenticated Lifecycle grant boundary.

The callers document has `schema_version: 1` and `callers`. Each caller binds
`tenant_id`, `executor_id`, `token_file` and `expires_at`. Tokens must be distinct;
current files and expiry are checked at every incoming request. Ongoing effects
also recheck Lifecycle authority and the stage registry at their existing boundaries.

The registry has `schema_version: 1` and `entries`. Each entry contains:

| Field | Meaning |
| --- | --- |
| `binding` | Every NativeBinding field except job/operation/attempt/campaign IDs and expiry; includes tenant, site, project, resource, executor, epoch, plan/intent/ownership digests and custody ID/generation |
| `expires_at` | Commissioning expiry; must cover the supplied grant |
| `plan_file` | Protected complete immutable stage intent; its digest must match the binding |
| `adapter` | One of the fixed names below |
| `configuration` | Adapter-specific protected connections and custody paths |
| `observer` | Independent owner connection and identities, or null for built-in OpenStack readers |

| Adapter | Configuration | Observation |
| --- | --- | --- |
| `vmware_capture` | `source` endpoint | Independent native owner |
| `vmware_export_archive` | `source`, exact `nfc` origin map, private `spool` | Independent archive/lease owner |
| `migration_copy_conversion` | Pinned `converter` runtime file, private `spool` | Independent copy/guest owner |
| `migration_image_import` | Distinct `writer`/`reader`, private `spool` | Built-in Glance readback |
| `openstack_resources` | Existing `runtime_file` | Built-in OpenStack readback |
| `migration_owner_protocol` | Fixed owner `endpoint` | Distinct authenticated owner protocol |

Image writer/reader entries have `user_id`, the existing four-service `endpoints`
map, and an `image` endpoint. Image endpoints are origins; Glance operations already
include `/v2`. The four OpenStack service connections retain their existing catalogue
prefixes and explicit microversions. NFC origins remain an explicit allowlist.

## Native account check

Run `lifecycle-migration-accounts --config /run/migration/accounts.json` from the
placed worker. This performs only identity/read/privilege queries. The result is a
redacted JSON observation; keep it in qualification custody. Failure returns a fixed
reason and never emits tokens, session keys, native response bodies or file paths.

The account document contains `schema_version: 1`, `scope`, `expires_at`, `source`
and `target`. Scope binds tenant/site/environment/executor UUIDs. Source identifies
the explicit VI JSON `api_version`, vCenter `instance_uuid`, `session_manager`,
`authorization_manager` and three `accounts`: `collector`, `writer`, `observer`.
Each source account contains `user_name`, `endpoint` and `privileges`; each privilege
check names one managed `entity` with `type`/`value`, nonempty `required` privileges
and explicit `forbidden` privileges. No privilege list is inferred from a role name.
Use the selected installed API's privilege requirements for the exact VM, copy
folder, datastore and resource pool. Reader/observer mutation privileges should be
explicitly forbidden in the approved list.

Target identifies `project_id` and the same three account roles. Each account has
`user_id`, `endpoints` and its exact approved Keystone `roles`. The probe validates
current token identity/project/expiry, observes roles, and reads compute and volume
limits plus network extensions. An extra role holds the account. Successful reads
do not prove create/delete/fence privileges; those require the separately authorized
native campaign. Reader/writer/observer identities and credentials must differ.

The manifest is checked during the probe. A changed manifest, rotated native
credential, stale session, foreign scope, missing/extra privilege result or shared
credential holds the probe. Rotate tokens through custody, then re-run; do not copy
credentials into Console, plan bodies or repository files.

## Application/guest/service protocol

The owner-protocol adapter provides bounded, pinned-TLS transport for a **supplied
implementation**. It does not implement an unspecified database replication method,
guest transformation, application fence or backup restore. It cannot replace the
four built-in whole-VM capture/export/conversion/import adapters.

An intent has `schema_version: 1`, `kind: migration_owner_protocol`, one exact
`stage`, a pinned `protocol_sha256`, and protocol-specific `parameters` containing
references, never secrets or data payloads. The owner receives `/v1/migration/effects`
with the full binding and immutable intent. It must enforce current custody/fencing
and idempotency. Its response binds the operation and receipt digest and explicitly
denies retry. Unknown outcomes are retained and cannot re-execute through this API.

The separate observer receives `/v1/migration/observations` with the same binding
and native object references. It must return current independently obtained evidence
bound to its commissioned identity and exact intent. Reads remain available after
a pause. Worker readback never supplies application readiness or target activation;
Lifecycle still requires its complete independent before/after evidence set.

## Native references checked 2026-10-07

- [VMware current session](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/SessionManager/moId/currentSession/get/)
- [VMware per-entity user privileges](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/AuthorizationManager/moId/HasUserPrivilegeOnEntities/post/)
- [OpenStack Identity v3](https://docs.openstack.org/api-ref/identity/v3/)

Documentation describes API contracts; it is not installed-platform qualification.
