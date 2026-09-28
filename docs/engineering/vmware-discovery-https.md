# Signed VMware discovery over bounded HTTPS

This is the implemented B10/B14 transport increment under the
[existing wave plan](../product/enterprise-workload-mobility-execution-plan.md).
It consumes the current VMware collector rather than creating another inventory
model, mutation client or compatibility entry point. No installed vCenter or
production data was used to verify this increment.

## Actual read path

`provisioner/controlplane/discovery/adapters/vmware_https.py` implements
`VmwareHttpsTransport`. Its `collect()` method invokes the existing VM-info
collector and emits the same `DiscoveryPage` records. Construct it inside the
trusted site integration with an immutable campaign, exact folder selection,
environment ID, bound signed campaign verifier, private credential source and CA.
It exposes no browser route, login, write method or alternate job submitter.

The connection goes to one signed IP address, while TLS validates the signed
origin hostname and the HTTP Host header retains that hostname. The client uses
only the CA bytes whose SHA-256 digest is in the signed native binding. It never
uses proxy environment variables, endpoint discovery, redirects, cookies, or
unverified TLS. Each request has a socket timeout and total deadline; the latter
shuts down slow header/body sockets. A serial lock and campaign-derived request
budget prevent unbounded retries or concurrent use of one transport instance.
These bounds are not a fleet-wide scheduler or estate performance qualification.

Only exact folder/datacenter-filtered VM list requests are permitted. A VM detail
request must name an ID actually returned by a permitted list in this client.
Unfiltered lists, alternate folders, arbitrary URLs, action queries, login paths
and unobserved IDs are refused before connecting. A list at the 4000-row REST
boundary remains inconclusive. Native error bodies never enter evidence.

Responses must be bounded JSON with unambiguous HTTP framing. Duplicate JSON
properties, nonfinite/overflowing numbers, excess nesting, compressed responses,
oversized bodies and truncated declared bodies are rejected. The client does not
log tokens or native error payloads. It does not retry rejected sessions.

## Native credential custody

`provisioner/controlplane/discovery/native_credentials.py` loads a private regular
file, refuses symlinks/FIFOs/public permissions, verifies an independent Ed25519
signature, and matches the session token's SHA-256 digest. It reloads on every
check and enforces a configured minimum revision plus an in-process high-water
mark. Persist that minimum across restarts and disaster recovery. A higher signed
revision is required for token or endpoint rotation; same-revision changes and
rollback are refused. A rotation during a request discards its result.

The envelope has exactly `binding`, `token`, and `signature`. The signature is
base64 Ed25519 over the ASCII bytes of the binding's sorted, compact JSON, using
`ensure_ascii=True` and `allow_nan=False`. The binding contains exactly:

| Field | Required meaning |
|---|---|
| `format`, `revision` | `hosting-vmware-read-credential/1` and a positive signed-64-bit revision. |
| `campaignDigest`, `environmentId`, `collectorId` | Exact admitted campaign digest, selected environment and existing VMware collector profile. The campaign digest already binds every scope component. |
| `selectionDigest` | SHA-256 of the exact `apiRelease`, ordered `folderIds` and `folderCoverageDigest` object, using the same canonical JSON. |
| `credentialReference`, `apiRelease` | The live enrolled native credential reference and selected `8.0.3.0` REST profile. |
| `origin`, `connectIp`, `caDigest` | HTTPS origin without a path; canonical pinned IP; digest of exact CA PEM bytes. |
| `tokenDigest` | SHA-256 of the high-entropy ASCII session token, not a login password. |
| `notBefore`, `expiresAt` | UTC interval covering the campaign, no longer than one hour. |

The native credential custodian must independently verify session identity,
read-only RBAC, exact native scope, installed API and endpoint before signing.
The repository does **not** generate those attestations from a user-supplied
success flag. Native issuance, lease renewal, Vault policy integration, file
publication and durable revision-floor custody remain deployment/integration
work. Do not put real envelopes, tokens or signing private keys in Git.

`BoundDiscoveryIngestVerifier.verify_read_credential()` additionally checks that
the material reference is the credential enrolled for this exact signed campaign.
It reuses current issuer/collector enrollment, signature and independent native
read-only witness verification. Native material signing keys cannot be the
campaign trust root or any enrolled issuer/collector signing key. An independent
native witness authority may also own material attestation.

The client verifies authority before connection, again after TLS before sending
the token, after receiving/decoding the response and before returning collection
pages. Expired campaigns, revoked identities, missing witnesses and changed
bindings fail closed. Existing ingestion separately verifies collector signatures
and mTLS before persistence; this client does not replace that requirement.

## OpenStack campaign-clock correction

The existing project collector now checks a trusted UTC clock before **every**
collection page and quota read, after both successful and failed requests, and
before emitting pages. Expired/not-yet-valid campaigns never issue the first GET;
clock regression and responses arriving at expiry are rejected. `clock=` supports
deterministic tests; it is supplied by the trusted site, not an HTTP parameter.
Native OpenStack HTTPS/credential composition is still separate work.

## Verification and evidence boundary

`tests/provisioning/discovery/test_vmware_https.py` uses actual loopback TLS,
ephemeral CA/endpoint certificates, independently signed campaign/material/witness
files and a synthetic REST server. It tests hardware collection, scope/path
refusal, key separation, credential revocation during a response, token rotation,
rollback, private-file rules, framing/JSON limits, deadlines and request budgets.
OpenStack negative clock tests reproduce the former first-read-after-expiry bug.
Installed-package tests import the new owners with `tools`/`scripts` blocked.

Successful fixtures remain `PARTIAL`/`VISIBLE_INVENTORY_ONLY`. This does not prove
native inventory completeness, real privilege enforcement, certificate-revocation
infrastructure, enterprise session issuance or a qualified migration route.
Normalizers, collector identities and policy formats are unchanged; this increment
adds transport/custody enforcement, not a new interpretation of inventory facts.
B14 still needs deployed site composition, original result-signature custody,
independent visibility reconciliation and native qualification. AHV/OpenStack
native clients, B17 dependency persistence and later migration waves remain open.

## Primary references

Broadcom's [REST authentication reference](https://developer.broadcom.com/xapis/vsphere-automation-api/latest/)
specifies `vmware-api-session-id` for subsequent requests. Its
[session lifecycle reference](https://developer.broadcom.com/xapis/vsphere-automation-api/latest/cis/cis-session/)
distinguishes session expiry/invalidation from already-running operations.
These references were checked on 28 September 2026 for authentication semantics;
their `latest` selector is not evidence that a particular installed release,
native scope or privilege set has been qualified. The transport's selected
VM-info API profile remains the one documented in the current collector.
