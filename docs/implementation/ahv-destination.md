# AHV destination implementation and qualification

AHV is a selectable migration destination. This implements the P08 M13 / P09
component path; it does **not** publish native AHV support or change an E3/E4 gate.
The first candidate is VMware → AHV, Linux, `VM_COLD_EXPORT`, BIOS, raw disks,
SCSI disk addresses and VirtIO NICs. UEFI, Windows, appliances, live/warm movement,
AHV sources and other directions require separate adapters or qualification.

## Native API contract

The destination uses explicitly pinned **v4.3** namespaces: `vmm`, `prism`,
`clustermgmt`, `networking`, `microseg`, and `iam`. Each namespace is independently
versioned. There is no SDK version negotiation, alternate API fallback, Terraform
VM data path, or VDDK dependency. An installed release must expose every selected
contract; a successful list request does not establish write or guest support.

| Purpose | Native request |
| --- | --- |
| Cluster and installed software | `GET /api/clustermgmt/v4.3/config/clusters/{cluster}` |
| Prism Central identity/build | `GET /api/prism/v4.3/config/domain-managers/{pc}` |
| Storage containers | `GET /api/clustermgmt/v4.3/config/storage-containers` |
| Subnets / VPCs | `GET /api/networking/v4.3/config/subnets` / `vpcs` |
| Categories | `GET /api/prism/v4.3/config/categories` |
| Flow policies | `GET /api/microseg/v4.3/config/policies` |
| Image import from converted copy | `POST /api/vmm/v4.3/content/images` with `UrlSource` |
| Create powered-off VM | `POST /api/vmm/v4.3/ahv/config/vms` |
| Task reconciliation | `GET /api/prism/v4.3/config/tasks/{task}` |
| Account/key/policy commissioning | IAM `authn/users/{user}`, `users/{user}/keys/{key}`, `authz/authorization-policies/{policy}` |

Image Service's `import_image` operation imports existing Prism Element images;
it is not an external VMware upload API. The adapter creates one `DISK_IMAGE`
per converted disk with a SHA-256 checksum and a private HTTPS `UrlSource`.
Each VM disk references that image using `DataSource.reference.ImageReference`.

References: [Nutanix v4 reference](https://www.nutanix.dev/api-reference-v4/),
[API user guide](https://www.nutanix.dev/nutanix-api-user-guide/),
[official VMM SDK models](https://github.com/nutanix/ntnx-api-golang-clients/tree/main/vmm-go-client),
[API key authentication](https://www.nutanix.dev/2025/02/21/nutanix-v4-apis-using-api-key-authentication-part-2/).
The model contract was checked against the official SDK; only an exact installed
cluster campaign can establish native behavior and release compatibility.

## Discovery and operator review

An AHV enrollment contains one `target_profile` stream at the Prism Central HTTPS
origin, `api_version: "v4.3"`, `cluster_id`, `prism_central_id`, and
`shared_resource_ids`. The existing `native_scope` is the commissioned project
UUID. Address pins, CA and credential paths, current authority and endpoint budgets
remain mandatory. Shared infrastructure IDs require explicit commissioning; no
resource is selected merely because its display name matches another resource.

The collector performs two identity reads and one or more separately authorized
reads per resource list. Explicit numbered pages contain at most 100 rows, up to
`min(max_pages, 10)` pages per list and 52 total reads under the existing lease.
Exact consistent totals, unique IDs and complete pages are required. Response
links are never followed. See the [bounded discovery increment](contextual-commissioning.md)
for service receipt checks, budget limits and failure behavior.
Unknown capacity reservations, boot drivers, network policy behavior, reachability,
application consistency and service behavior remain explicit evidence obligations.
Raw format is an adapter candidate, not a claimed API-advertised capability.

Inventory v1.5 introduces a discriminated schema-version-2 AHV target profile and
an optional typed `destination` review field. AHV reviews require it. The operator
selects observed storage, VPC/VLAN scope, categories, policies and separate
quarantine/production subnets for **every** source NIC, and one contiguous SCSI
slot for **every** source disk. Source facts cannot be overridden. Fleet targets
identify their platform. Configuration pulls project the same immutable AHV
profile into platform-specific capability rows.

Inventory's authenticated migration input v2 carries the selection to Planning.
The resulting destination digest binds the review, recipe and import artifact.
AHV recipes use schema version 2; the composed migration uses schema version 3.
Existing OpenStack records retain their previous semantics. Changed observations,
expired profiles, revoked enrollment, changed mappings, wrong tenancy and incomplete
mappings invalidate review/admission through the existing owner boundaries.

## Commissioning and execution

The Lifecycle worker registry now accepts adapter `ahv_destination`. Its protected
configuration has `writer`, `reader` and `staging`; `observer` is `null` because
independent readback is native to this adapter. Each account record contains:

- `user_id`, `key_id`, and `credential_sha256` from the protected API-key creation receipt;
- `authorization_policies`, mapping policy UUIDs to exact canonical native policy digests;
- `endpoint`: the existing `base_url`, `address`, `ca_file`, `token_file` structure.

Writer and observer must have different principal IDs and different credential
bytes, on the same pinned origin. The read-only account commissioning command
also supports schema version 2 with target `platform: "ahv"`, project/PC/cluster
IDs and distinct collector/writer/observer accounts. Source commissioning remains
unchanged. Live IAM reads verify active service accounts, active unexpired keys and
unchanged policy records. IAM only returns an API-key secret at creation: the
protected creation receipt supplies that identity linkage. A GET of a named user
alone is deliberately **not** described as proof of the current caller. These
checks do not prove effective write permissions or cross-project denial.

The immutable plan is validated in `application/ahv_plan.py`: scope/custody,
API pins, reviewed destination digest, conversion artifact digest, name, CPU/RAM,
complete disks/NICs, selected categories/policies, approved shared resource IDs and
a bounded deadline. The reviewed base plan's native operation is the exact
`import_target` artifact. Independent account, recipe, custody and stage authority
are still required by the existing runtime.

Before the first create, the worker verifies every converted file's size,
SHA-256/SHA-512, raw virtual size and successful sector comparison against the
same tenant/job/plan/custody conversion receipt. It rechecks the native cluster,
storage and selected network/security resources. It imports all disks, then creates
a **powered-off** VM with disconnected NICs attached only to quarantine subnets.
Production subnet IDs are retained for the separately approved activation protocol.
No API import result authorizes first boot, target writes or application readiness.

Each POST has a deterministic per-operation/per-resource `Ntnx-Request-Id` recorded
before submission. The task receipt is committed before polling. Task IDs may
include the native `ergon:` prefix. Successful tasks must identify exactly one
created entity; ambiguous affected entities remain held. Lost POST responses,
failed/unknown tasks, restarts and incomplete imports never replay creation.
Independent reconciliation reads retained tasks and objects, and checks project,
custody marker, image digest/placement, power, firmware, CPU/RAM, all disks and
image provenance, all NICs and categories. If the installed API omits disk image
provenance, the adapter holds instead of guessing. Partial results remain held and
retain custody for operator reconciliation.

## Private artifact staging

`staging` has an absolute private `root` for grants, private conversion `spool`,
and a commissioned HTTPS `origin`. Run the worker's additional TLS listener:

```sh
python -m lifecycle_worker.bootstrap.ahv_staging --config /run/ahv/staging.json
```

Its protected configuration contains the same `root`, `spool`, `origin`, plus
`addresses` (the explicitly authorized Prism/Image Service/CVM source IPs),
`tls_cert_file`, and `tls_key_file`. Commission DNS, routing/firewalls and a CA
trusted by the actual native image downloader. Never enable insecure URL retrieval.
Both directories require mode 0700; secrets/grants require 0600. The listener
serves only exact opaque grant paths over HTTPS, checks peer address, verifies
artifact digests, rejects symlinks/path traversal and stops on revocation or expiry.
Access logging and forwarded-header trust are disabled. Grant URLs never enter
Console, Lifecycle control-plane bodies or the durable native journal.

Grants are revoked after verified image import. An uncertain import retains its
grant only until its bound expiry so a submitted native fetch can finish; remove
expired grant files under the site's retention policy. Conversion bytes are not
deleted by import. Cleanup, source snapshot consolidation, image/VM deletion and
credential revocation remain separately authorized, independently observed owner
protocol stages. Cleanup must reconcile every outstanding task before deleting
artifacts or releasing custody. Recovery follows the existing pre-write rollback
and post-write preservation/forward-or-reverse recovery boundaries.

## Qualification and release gate

Component checks use synthetic Prism responses, actual TLS, private file delivery,
versioned contracts, PostgreSQL custody tests and the actual Vue review. They are
**E2 only**. `.github/workflows/ahv-destination.yml` runs the full migration suites
with PostgreSQL and the five browser scenarios on the default branch's PRs.

The [Q08 AHV campaign](../qualification/campaigns/ahv-destination-tranche.md) must run
against a commissioned Prism Central/AOS/AHV tuple and an approved Linux guest.
No E3 record, approved native credentials, connected AHV lab or receiving sign-off
is supplied by this implementation. Operational qualification remains held until
those original observations and approvals exist.
