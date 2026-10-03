# Project-scoped OpenStack discovery over bounded HTTPS

Reviewed 1 October 2026. This B10/B16 implementation continues the
[existing B01–B50 wave plan](../product/enterprise-workload-mobility-execution-plan.md).
It connects the existing project collector to actual Nova, Cinder, Neutron and
Glance HTTPS GETs. No installed vendor environment was contacted in development.

## Selected native contract

`provisioner/controlplane/discovery/adapters/openstack_https.py` owns
`OpenStackHttpsTransport`; `adapters/openstack_credentials.py` owns the signed
project-token reader. The exact collector identity is `openstack-project-https-3`.
A newly admitted matching campaign, independent credential witness and protected
credential material are required. An arbitrary collector ID is not an alias.

| Logical service | Exact catalog-root suffix | Allowed reads | Pinned API contract |
|---|---|---|---|
| compute | `/v2.1/<project>` | `servers/detail`, `os-quota-sets/<project>` | `OpenStack-API-Version: compute 2.79` |
| volume | `/v3/<project>` | `volumes/detail`, `os-quota-sets/<project>` | `OpenStack-API-Version: volume 3.60` |
| network | `/v2.0` | `ports`, `quotas/<project>` | Neutron v2.0 path; no invented microversion header |
| image | `/v2` | `images/<VM-referenced-image-id>` only | Glance Image API v2; signed minimum evidence contract `2.7`, no request microversion header |

These are deliberately selected client contracts, not claims about a supported
OpenStack distribution/release tuple. No `latest` negotiation or older-version
fallback is used. Successful compute/volume responses must contain exactly one
matching version header. Missing, duplicate or different versions hold the read.
The native site must independently qualify its service versions, extensions,
backend drivers, read roles and exact response visibility.

Safe explicit reverse-proxy path prefixes are supported. Endpoints must be HTTPS
roots without query/fragment delimiters, userinfo, URL controls, percent escapes,
backslashes, dot segments or empty path components. Root validation rejects input
that URL parsing would otherwise silently normalize. The four service URLs,
endpoint identities, literal IP addresses and exact CA digests are signed; the
client neither discovers endpoints from Keystone nor follows catalog/response URLs.

## Hardware, storage and referenced-image observation contract

The second collector profile retains Nova's embedded server allocation: `vcpus`
becomes `vcpuCount`, RAM and swap MiB become bytes, and flavor root/ephemeral GiB
become explicitly named nominal allocation facts. Numeric coercions, booleans,
negative values and signed-64-bit byte overflow are rejected. Missing or partial
flavor fields stay unknown; a legacy flavor ID does not trigger another lookup.
The existing normalizer consumes canonical CPU/memory facts. A flavor's root size
is not `diskCapacityBytes`: volume-backed roots, image minimums, ephemeral disks,
shared volumes and complete attachment coverage must be reconciled separately.

Nova image UUIDs, explicitly volume-backed empty image references, volume UUIDs
and per-volume `delete_on_termination` booleans are retained. A missing deletion
flag preserves the relationship but leaves disposition unknown. Cinder detail
responses retain attachment/server/volume UUIDs and an optional guest device label.
Missing and explicitly empty sets are distinct; duplicate identities, mismatched
volume IDs and oversized relationships hold collection. The limits are 64 Nova
relationships, 32 Cinder relationships and the existing 8,192-byte fact bound.
Sorted relationship order does not establish boot order or guest disk order.

For each non-volume-backed Nova server, selector 3 also reads exactly the referenced
Glance image by UUID. It does not enumerate the image catalog or download image bytes.
The retained whitelist is name/status, disk/container format, size/virtual size,
minimum disk/RAM, visibility, owner, protected/hidden state, secure multihash
algorithm/value and selected architecture/OS/machine/firmware/disk-bus metadata.
The secure hash pair must be complete and syntactically bounded; the legacy Glance
`checksum` is deliberately not retained as the integrity claim. Shared/public image
ownership is observed rather than forced to equal the workload project. Volume-backed
servers trigger no Glance read.

These are observations, not compatibility. A qcow2/bare label, architecture or UEFI
property does not prove the guest has required drivers, that keys are portable, that a
target supports that format, or that the image is safe for a migration route. Arbitrary
image properties, flavor extra-specs, host names, connector credentials, metadata and
user data cannot enter qualification through this path. A complete relationship is not
proof of writer exclusion, permission to delete, a consistency group or a complete
migratable disk image.

The previous OpenStack selectors are retired, not forwarded. Deployments must enroll
`openstack-project-https-3`, issue a fresh matching campaign/witness/credential
binding, collect a new signed generation, and reassess its exact digest. Old signed
results remain immutable history; they are not relabelled or silently enriched.

## Signed project-token custody

`SignedFileOpenStackCredentialSource` reloads an independently signed private
regular file for every authorization check. Its envelope contains exactly
`binding`, `token`, and `signature`. The Ed25519 signature covers the binding's
canonical sorted compact ASCII JSON (`ensure_ascii=True`, `allow_nan=False`).
Duplicate JSON fields, malformed types, non-finite/oversized values, public file
permissions, symlinks, FIFOs, tampering and rollback are rejected. Files are bounded
to 65,536 bytes; tokens are bounded printable ASCII and never appear in ordinary
errors, object representations or discovery observations.

Required binding fields are:

| Fields | Obligation |
|---|---|
| `format`, `revision` | `hosting-openstack-read-credential/1`; positive signed-64-bit revision. |
| `campaignDigest`, `environmentId`, `collectorId`, `credentialReference` | Exact campaign/environment/collector and live enrolled native credential reference. |
| `scopeType`, `projectId`, `userId` | Independently verified project-scoped token, exact project and native user identity. Domain, system and unscoped credentials are not admitted. |
| `catalogDigest`, `regionId`, `interface` | Digest of independently verified catalog evidence, selected region and `internal` or `public` interface. `admin` endpoints are not admitted. |
| `apiVersions` | Exact logical-service mapping: compute `2.79`, volume `3.60`, network `2.0`, image `2.7`. The image value binds this reviewed feature floor; it is not sent as a Glance microversion header. |
| `endpoints` | Exactly compute/volume/network/image records, each with `url`, unique `catalogEndpointId`, canonical `connectIp`, and `caDigest`. Every URL must equal the selected service root. |
| `tokenDigest`, `tokenIssuedAt`, `tokenExpiresAt` | SHA-256 of token bytes and independently verified native token validity. A custody lease does not extend native token expiry. |
| `notBefore`, `expiresAt` | UTC custody interval covering the campaign, at most one hour and ending no later than token expiry. |

The material signer must be independent of campaign root, issuer and collector
keys. `BoundDiscoveryIngestVerifier` separately requires current enrollment and a
native read-only witness for the exact project/environment scope. The custodian
must verify scope, service catalog and read-only privileges across all four
services, including ownership-field visibility; possession of token bytes and a
local GET-only client cannot prove those facts. No privileged account fallback
is introduced when Cinder or another service omits a required ownership field.

New signed revisions can rotate tokens between requests. The token must be valid
at use and cover the admitted campaign. Changed same-revision material, lower
revisions and mid-request rotation are refused. Minimum revisions and in-process
high-water marks are not persistent restart/DR protection. Token issuance,
renewal/revocation, Vault publication and independently protected durable revision
floors remain separate integration and qualification work.

## Request, response and publication boundaries

The client owns one serial sequence: the three project collection page chains, followed
by their three project quota reads and then one exact Glance GET for each distinct
non-null image UUID referenced by the collected Nova servers. Only the next exact service/path/parameter
combination is admitted. Pagination uses the last observed native UUID, never a
server-supplied destination. Nova requests exclude all-tenant enumeration; Neutron
port requests additionally carry the exact signed project filter. Native row
ownership and duplicate identities are checked by the existing provider parser
before the next marker is admitted. Image reads, objects and all attempted requests consume the same finite
campaign budgets; failed/replayed/skipped requests close that client instance.

The actual provider-neutral `discovery/native_https.py` mechanism is shared with
VMware and AHV. Its new bounded public-header inputs cannot replace authentication,
Host, framing, cookie or proxy headers. It checks pinned TLS hostname/IP/CA,
response framing and JSON, socket and total deadlines, and closes buffered readers
and sockets on both success and holds. There are no proxies, DNS discovery,
redirects, cookies, automatic retries, login or plaintext reconnects.

Current authority is checked before connecting, after TLS before token transmission,
after response decoding and before collection returns. Revocation/rotation/expiry
or service failure discards the scan. The pure collector's diagnostic-page handling
cannot accidentally turn a native-client hold into publishable inventory.
Successful and empty native-client scans remain `PARTIAL / VISIBLE_INVENTORY_ONLY`.
A visible page chain is neither a point-in-time snapshot nor independent proof of
complete inventory or absent resources.

## Verification and remaining work

Real loopback TLS tests use three separate service origins, ephemeral certificates,
synthetic tokens and independent signed authority records. They cover project and
service isolation, exact protocol versions, pagination, budgets, private files,
key independence, revocation, rotation, stale revisions, TLS identity, strict
framing/JSON, proxies and deadlines. Separate header/endpoint regressions cover
normalization and framing/custody overrides. Existing VMware/AHV regressions remain
in force; installed-wheel tests require the actual owners outside the checkout.
These tests do not qualify a deployed OpenStack environment.

Discovery-page, normalizer 2, profile resolution 3 and policy capsule/realization 2
formats are unchanged. Changed observations require fresh digest-bound reviews.
The installed collector command and original signed/authenticated publication are
implemented; revisioned application drafts and signed owner decisions also exist.
Unattended site commissioning, durable cross-process custody/scheduling, independent
visibility reconciliation, Glance metadata, complete hardware/driver/key coverage,
external dependency verification and full owner workflows remain open.
No migration, native mutation, execution grant or production qualification is added.

## Primary references

Consulted 29 September and rechecked 1 October 2026. These sources establish API semantics, not installed
qualification or enterprise approval:

- [Keystone Identity v3](https://docs.openstack.org/api-ref/identity/v3/) describes
  project scope, token validity and catalog region/interface/endpoint identity.
- [Nova microversions](https://docs.openstack.org/api-guide/compute/microversions.html)
  describes explicit version selection, response version headers and rejection
  of unavailable versions; the client does not use `latest`.
- [Nova Compute API](https://docs.openstack.org/api-ref/compute/) defines the
  server-detail, embedded allocation units, image and attachment fields, marker/limit
  and project quota reads. [Nova microversion history](https://docs.openstack.org/nova/latest/reference/api-microversion-history.html)
  records embedded allocation details from 2.47; this collector still pins 2.79.
- [Cinder API v3](https://docs.openstack.org/api-ref/block-storage/v3/) and its
  [microversion history](https://docs.openstack.org/cinder/latest/contributor/api_microversion_history.html)
  distinguish the caller's token project from URL syntax and document the volume
  API header. This client intentionally retains explicit project-root paths.
- [Neutron API v2](https://docs.openstack.org/api-ref/network/v2/) defines project
  filters, ports and quota reads. Deployment policy controls field visibility;
  hidden fields do not acquire defaults or become qualified capability evidence.
