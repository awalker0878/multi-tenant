# P09-A — Any-to-any workload migration completion

Approved scope: all nine directed combinations of VMware, OpenStack and Nutanix
AHV, including separate installations of the same platform. Baseline:
`eda64354816b4884530118f6595c037a5a556807`. This tranche completes existing P09
obligations and affected P07/P08 outcomes; P11 remains pilot and supported release.

The audit's six P0 findings are tracked to the implementation packages below.
Engineering evidence and installed-platform qualification are separate gates.

| Finding | Required outcome | Packages |
| --- | --- | --- |
| G1 | Each platform is independently usable as source and destination | A02, A06–A08 |
| G2 | Exact directional support records gate planning and current admission | A01, A11 |
| G3 | Prepare copied guests and independently observe boot, drivers, storage, network and identity | A04 |
| G4 | Bind source/target security semantics and verify permitted and denied paths | A05 |
| G5 | Require individual IPAM, DNS, identity, time, trust, logging, monitoring and backup outcomes | A03, A05 |
| G6 | Implement selected consistency, continuation and recovery mechanisms | A09 |

| Package | Delivery | Engineering | Native qualification |
| --- | --- | --- | --- |
| A01 | Connected exact directional eligibility and current admission | Implemented; local checks pass; full gates pending | Not established |
| A02 | Role-aware discovery, account commissioning and platform mechanisms | Implemented; local checks pass; full gates pending | Not established |
| A03 | Contextual requirements and confirmed downstream inputs | Implemented; local checks pass; full gates pending | Not established |
| A04 | Copy-only guest preparation and independent health probes | Implemented; local checks pass; full gates pending | Not established |
| A05 | Security mapping and individual enterprise-service outcomes | Implemented; local checks pass; full gates pending | Not established |
| A06 | OpenStack source capture and composed destinations | Implemented; local checks pass; full gates pending | Not established |
| A07 | AHV source capture and composed destinations | Implemented; local checks pass; full gates pending | Not established |
| A08 | VMware destination and all nine composed directions | Implemented; local checks pass; full gates pending | Not established |
| A09 | Data consistency, durable continuation and recovery | Implemented; local checks pass; full gates pending | Not established |
| A10 | Console, fleet, campaign and observed progress parity | Implemented; local checks pass; full gates pending | Not established |
| A11 | Directional conformance, main CI and P10 handoff | Implemented; local checks pass; full gates pending | Not established |

## Completion boundary

The software changes address G1–G6 through A01–A11. Full closure still requires
PostgreSQL/PHP and hosted runtime verification, qualified converter/guest artifacts,
installed application/storage owner implementations, native campaigns for every
selected direction and independent receiving acceptance. The shipped Windows
profile examples are bounded driver preparation, not a universal guest converter.
This phase remains in progress until those requirements have evidence.

## Invariants

- Native APIs are authoritative; Terraform is outside the VM data path and VDDK
  is not required. Whole-VM transformations operate on a migration copy.
- Source/destination roles compose through capabilities; native metadata and
  unsupported constraints remain explicit. A method enum is not an implementation.
- Every required guest, security, service and application outcome must be observed
  independently before production activation. Declarations and API receipts are
  not operational acceptance.
- Before possible destination writes, rollback requires target fencing and proof
  of no divergence. After possible writes, preserve changes and reconcile through
  forward recovery or a qualified reverse procedure. Unknown outcomes remain held.
- Test peers are E2 evidence. Each advertised direction/version/guest/method needs
  separate E3 evidence and the applicable E4 receiving acceptance. Missing lab
  access never turns an unimplemented handler into an external-only blocker.

## External qualification inputs

Exact installed platform/API/backend versions, approved guest images and licenses,
application consistency and recovery procedures, platform/service credentials,
network and security mappings, enterprise-service interfaces, conversion artifacts,
measured operating objectives and independent receiving owners are required.
Repository development does not itself authorize operations against a platform.

## Acceptance

Engineering exit requires concrete mechanisms and connected consumers for the
approved scope, compatibility and failure tests, and current architecture/runbooks.
Native exit requires a functioning secured enterprise-integrated workload for an
exact tuple in every direction, plus every additional advertised variant. Include
unsupported combinations, failed prerequisites, lost responses, partial integration,
process interruption, retry/resume, cutover and both recovery boundaries. Retain all
failures and source/artifact identities. P10/P11 own operating release acceptance.

## Source capture contracts

OpenStack cold capture uses Nova 2.1 `createImage` for a local root and a separate
Cinder 3.0 snapshot → isolated volume → image upload for every attached volume.
It requires a stopped source, exact disk inventory, unencrypted single-attachment
volumes, private Glance images and SHA-256/SHA-512 integrity. Ephemeral/swap disks
and unknown encryption or sharing state remain held. No production volume is
uploaded directly, and a lost POST response is not replayed. Partial resource IDs
remain in the native custody ledger for reconciliation and cleanup.

The shared archive retains declared raw, qcow2 or VMDK bytes. Version 3 conversion
uses explicit input/output formats, rejects external backing and encrypted images,
and compares sectors before accepting its output. This is disk conversion; it does
not establish a prepared guest. Protected runtime composition wires independent
source-image readers; image and byte evidence never asserts application readiness.

API basis: [Nova compute reference](https://docs.openstack.org/api-ref/compute/),
[Cinder v3 reference](https://docs.openstack.org/api-ref/block-storage/v3/),
[Glance v2 reference](https://docs.openstack.org/api-ref/image/v2/), and
[QEMU disk image formats](https://www.qemu.org/docs/master/system/images.html).
The new component peers and local TLS tests are synthetic E2 evidence, not native
platform qualification.

## Directional implementation matrix

This table describes executable adapter composition. It is not a native support
claim. The runtime support matrix is produced from the commissioned expansion
tranche and current Assurance records. It names exact installation, platform/API,
network/storage backend, guest, method, artifacts, service/security/data/recovery
requirements, exclusions and evidence for each route. The reverse route and a
second installation of the same platform each require their own records.
No native direction or guest/API variant is qualified by these software changes.

| Direction | Source capture/export | Destination import | Qualified platform/API/guest variants |
| --- | --- | --- | --- |
| VMware → VMware | Exact stopped snapshot/clone and OVF/NFC archive | VI JSON OVF import/NFC lease | None established |
| VMware → OpenStack | Exact stopped snapshot/clone and OVF/NFC archive | Glance and mapped OpenStack target | None established |
| VMware → AHV | Exact stopped snapshot/clone and OVF/NFC archive | Prism image and mapped VM | None established |
| OpenStack → VMware | Nova/Cinder isolated images and Glance archive | VI JSON OVF import/NFC lease | None established |
| OpenStack → OpenStack | Nova/Cinder isolated images and Glance archive | Glance and mapped OpenStack target | None established |
| OpenStack → AHV | Nova/Cinder isolated images and Glance archive | Prism image and mapped VM | None established |
| AHV → VMware | Prism VM-disk images and protected image archive | VI JSON OVF import/NFC lease | None established |
| AHV → OpenStack | Prism VM-disk images and protected image archive | Glance and mapped OpenStack target | None established |
| AHV → AHV | Prism VM-disk images and protected image archive | Prism image and mapped VM | None established |

The OpenStack source mechanisms use Nova 2.1, Cinder 3.0 and Glance v2;
AHV uses explicitly enrolled Prism v4.3 interfaces; VMware VI JSON requires an
exact four-part API version. These are implemented protocol bounds, not proof
that every product release exposing them is supported. Record actual product,
API and backend versions in the tranche before its qualification campaign.

All cold-copy routes require stopped consistent sources, exact all-disk inventory,
private custody, capacity bounds, approved offline converter/guest artifacts,
separate writer and observer identities, quarantine network placement, owner
service/security mappings and post-write recovery. Unsupported encryption, shared
or external disks, unknown backing chains, incomplete inventory, ambiguous tasks,
unobserved device mappings and unqualified guest configurations remain held.
Linux and Windows are explicit guest profile selections; appliances prohibit
unapproved mutation. A profile or method enum does not confer support.

## Connected outcomes and recovery

Version 3 commissioned recipes and version 4 composed migration plans carry the
full direction, exact route digest, owner-input digest, guest profile and outcome
requirements. Planning and Lifecycle enforce the same outcome contract and require every dataset and individual enterprise
service. Qualification binds the guest outcome hashes as well as the guest
transformation artifact. Byte-loss objectives and time-loss bounds are distinct;
a route needs an explicit byte bound for nonzero data-loss qualification.

The independent observation process reads commissioned native services through
separate identities and exact subject/predicate manifests. Policy verification
requires both allowed and denied traffic observations. No browser declaration,
writer receipt, image hash or aggregate "services ready" flag establishes boot,
security equivalence or enterprise acceptance.

Recovery preserves these requirements, the exact original direction and the
first possible target business-write marker. A pre-write rollback requires target
fencing and no divergence; post-write recovery preserves target changes and uses
the qualified forward/reverse procedure. Transfer continuation reuses only the
recorded read operation with immutable image identity, verified local prefix,
current authority and custody. Uncertain native writes are never replayed as reads.

## Operator and verification handoff

The Console presents all nine directions, observed destination mappings, contextual
account requirements and current qualification blockers. Native job views expose
persisted operation timing, independently observed stage completion and authenticated
completed-disk byte counters from the worker custody journal. Unavailable progress
remains unknown. Stage counts are not a byte-transfer percentage or an estimated
completion time.

[The any-to-any runbook](../operations/runbooks/any-to-any-migration.md) describes
commissioning and the qualification sequence. Existing P10/P11 native, operating,
security and independent receiving gates remain authoritative. Development tests
must never populate those gates with synthetic acceptance.

## Native interface references

Adapter conformance was checked against the published interfaces below. Versioned
installation evidence is still required; documentation is not a migration result.

- [Prism v4.3 VM-disk image source](https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.3/languages/python/ntnx_vmm_py_client.models.vmm.v4.content.VmDiskSource.html): source VM and disk identities.
- [VI JSON OVF import specification](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/OvfManager/moId/CreateImportSpec/post/): native import specification and file mappings.
- [VI JSON NFC lease completion](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/HttpNfcLease/moId/HttpNfcLeaseComplete/post/): completion response semantics.
- [Prism task identifiers and batching](https://www.nutanix.dev/2026/04/13/nutanix-v4-api-batches-a-technical-use-case/): opaque base64-prefixed task identifiers.

## Retained local results

[Local evidence](../../verification/p09/any-to-any-local/README.md) records 1,637
passing Python tests, 146 explicit database skips and nine passing browser journeys.
It also retains original failures, hashes and the remaining qualification limits.
