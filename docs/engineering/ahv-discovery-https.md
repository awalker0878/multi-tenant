# Signed AHV discovery over bounded HTTPS

This B10/B15 implementation continues the [existing B01–B50 wave plan](../product/enterprise-workload-mobility-execution-plan.md).
Reviewed 28 September 2026 (America/Toronto). It connects the current VMM v4.0
collector to actual HTTPS GETs; it does not issue API keys, admit campaigns, sign
results, mutate native resources or qualify an installed Nutanix environment.

## Native contract and authentication

`provisioner/controlplane/discovery/adapters/ahv_https.py` owns
`AhvHttpsTransport`. Its `collect()` consumes an already admitted VM-only campaign,
a bound signed campaign verifier, an independently signed credential source and
protected CA bytes. It invokes `collect_ahv_vms` and returns existing `DiscoveryPage`
records. Scope, environment, collector and API profile must match before any read.

The sole permitted operation is GET `/api/vmm/v4.0/ahv/config/vms`, with the exact
cluster/extId filter derived from the campaign, zero-based consecutive `$page`,
and `$limit` bounded by the campaign and the API's 100-row maximum. Caller filters,
extra query fields, arbitrary URLs, actions and skipped/repeated pages are refused.
No server-supplied URL is followed. Each attempt consumes a page/request budget;
a transport/HTTP failure latches that client closed. A new admitted campaign is
required after failure or exhaustion. There is no basic-auth, login or retry fallback.

The transport sends `X-Ntnx-Api-Key` only after TLS and fresh authorization checks.
The native credential custodian must provision and verify a suitably scoped service
account, its API key, installed API support and actual read-only permissions.
The native RBAC witness and signed campaign are checked independently of possession
of that key. An example using an administrator role is not a least-privilege design.

## Signed credential custody

`adapters/ahv_credentials.py` owns `SignedFileAhvCredentialSource` and
`AhvApiKeyMaterial`. The envelope is a private regular file with exactly `binding`,
`apiKey` and `signature`. It is read again for every authorization check. Symlinks,
FIFOs, public permissions, oversized/ambiguous JSON, tampering, revision rollback
and changed same-revision bindings are refused. API-key bytes are excluded from
material representations, ordinary errors and discovery observations.

The independent Ed25519 signature covers the binding's canonical sorted compact
ASCII JSON, with `ensure_ascii=True` and `allow_nan=False`. Required binding fields:

| Fields | Meaning |
|---|---|
| `format`, `revision` | `hosting-ahv-read-credential/1`; positive signed-64-bit revision. |
| `campaignDigest`, `environmentId`, `collectorId` | Exact campaign digest, authorized environment, and `nutanix-ahv-v4.0-hardware-2`. The digest already binds all scope components and budgets. |
| `credentialReference`, `serviceAccountId`, `apiVersion` | Enrolled native credential reference, canonical service-account UUID and the selected `v4.0` profile. |
| `origin`, `connectIp`, `caDigest` | HTTPS origin without a path or userinfo; canonical literal IP; SHA-256 of exact CA PEM bytes. Controls/whitespace and unpinned endpoint discovery are forbidden. |
| `apiKeyDigest` | SHA-256 of the exact ASCII API-key bytes, not a login password. |
| `notBefore`, `expiresAt` | UTC interval covering the entire campaign, at most one hour. This is the signed custody lease, not a claim about native API-key expiry. |

Material signers must not be the campaign trust root or any enrolled issuer or
collector key. The credential reference must match live enrollment and the current
independent read-only witness. Authority is checked before connection, after TLS
before transmitting the key, after decoding and before collection returns.
Revocation or key/binding rotation during a read discards its result. Collection
must not convert a revoked campaign into publishable diagnostic pages.

A higher revision can rotate material between page reads without changing campaign
scope. Minimum revisions and in-process high-water marks do **not** supply durable
restart/disaster-recovery protection. Key issuance/revocation, Vault publication,
protected persistent revision floors and deployment custody remain open work.
Real keys and signed material must never be committed to the repository.

## Shared transport ownership

`provisioner/controlplane/discovery/native_https.py` now owns the actual common
HTTPS GET implementation used by both AHV and VMware. The VMware adapter retains
its native path allowlist, credential format, list-derived VM IDs and response
semantics. Neither adapter wraps the other; shared transport has no vendor imports
or platform selection. The generic protected-file and JSON helpers remain separate.

The common mechanism connects to the signed literal IP, verifies the signed TLS
hostname with the signed CA bytes, and sets the corresponding HTTP Host header.
Proxy environment variables, redirects, cookies, DNS endpoint discovery, automatic
retries and plaintext reconnects are not used. Bounds cover response size, strict
JSON, HTTP framing, socket inactivity and the total read deadline, including trust
loading, TLS, HTTP and decoding. Cancellation closes buffered response readers and
sockets. Native error bodies and credentials never become ordinary error evidence.
The extraction retains the earlier VMware deadline and revocation regressions.

## Evidence and completion boundary

Even an internally consistent total or empty response is only a **visible** list.
Successful native-client collections are `PARTIAL` with `VISIBLE_INVENTORY_ONLY`;
permission/protocol failures stay `UNKNOWN`. The underlying pure parser can describe
a complete visible page chain, but the HTTPS client cannot infer independent
inventory coverage from it. Original collector signatures, authorized mTLS ingest,
generation pinning and signed review remain required before assessment use.

Collector identities, normalizer 2, profile resolution 3 and policy capsule/
realization 2 are unchanged. A changed observation has a new digest and needs a
fresh review; old evidence is not relabelled. This client does not implement a site
service runtime or native result-signing/publication path. The separate
[OpenStack HTTPS client](openstack-discovery-https.md) now implements bounded project
reads; independent visibility reconciliation, B17 owner/dependency persistence and later
provisioning/migration effects remain unfinished.

Tests in `tests/provisioning/discovery/test_ahv_https.py` exercise actual loopback TLS
with ephemeral keys/certificates and independent signed authority records: two-page
collection, empty visibility, exact paths, key isolation, revocation/rotation,
private files, revision floors, malformed bodies/framing, deadlines and page budgets.
The existing VMware tests exercise the same common transport without weakened gates.
Installed-package checks require both adapter owners and the common mechanism to
resolve outside the checkout. These are protocol fixtures, not native qualification.

## Primary sources and scope

[Nutanix's REST API-key example, 21 February 2025](https://www.nutanix.dev/2025/02/21/nutanix-v4-apis-using-api-key-authentication-part-2/)
documents service-account-only API-key authentication and use of the key header for
VM listing, with PC/AOS prerequisites for that example. The
[5 August 2025 API/SDK update](https://www.nutanix.dev/2025/08/05/update-api-key-authentication-in-nutanix-rest-api-and-sdk-v4-1/)
confirms that `X-Ntnx-Api-Key` remains valid while SDK convenience methods change.
The [VMM v4.0 VM API reference](https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0/languages/python/ntnx_vmm_py_client.api.vm_api.html)
documents page/limit bounds and cluster/extId filtering for VM lists.

Consulted 28 September 2026. These references support authentication/request semantics,
not blanket version compatibility, least privilege, inventory completeness or a
qualified migration route. Exact installed PC/AOS/API/IAM/entitlement combinations
still require independent site evidence under the existing wave gates.
