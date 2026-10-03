# Platform capability registry and placement evidence boundary

The engineering registry at `sources/capabilities/platform_registry.json` covers
97 workload capability dimensions for each of Nutanix AHV/Flow, VMware vSphere/NSX
and OpenStack. The single vocabulary owner is
`provisioner/domain/capabilities.py`. Both the registry validator and native
qualification validator consume that vocabulary; there is no second hard-coded
network-only list or compatibility expansion.

This is the programme's reviewed capability scope, not an assertion that every
vendor feature is implemented. Unrecognized requirements require a reviewed
catalogue extension; they are rejected rather than silently ignored. Platform
family, installed product/API/provider tuple, feature entitlement, implementation
coverage and native qualification are different facts.

## Coverage dimensions

| Group | Assessed dimensions |
|---|---|
| Compute | Create, resize, power and delete; CPU topology, reservations, affinity, NUMA, pinning, huge pages, GPU/vGPU/PCI, firmware, secure boot and vTPM. |
| Storage | Boot/data volumes, placement, QoS, encryption, consistency, snapshot chains, export/import, conversion, shared disks, disk order and resize. |
| Network | Domains, IPv4/IPv6, routing, load balancing, multiple NICs and their order, address preservation/translation, trunks, SR-IOV, QoS and readback. |
| Security | Distributed and gateway policy, insertion, edge contexts, auditing, policy equivalence and controlled ingress/egress. |
| Guest | Linux, Windows and appliances; customization, drivers, identity and readiness. |
| Discovery | Collection, page completeness, freshness, scope, quotas, reviewed dependencies and no-change adoption. |
| Migration | Dataset and incremental transfer, integrity, consistency groups, quiescing, fencing, isolated rehearsal, final sync, traffic switch, activation, pre-write rollback, post-write recovery, reverse sync and source retention. |
| Services | DNS registration, identity join, time, trust, log forwarding, monitoring and backup/restore. |
| Operations | Capacity, IPAM, staging and concurrency budgets; reconciliation, HA restart, control-plane DR, evidence custody, privileged access and release qualification. |

Each platform explicitly carries every capability row. Missing rows are invalid;
no default row or vendor-name inference fills a gap. `capability_catalog_sha256`
binds the reviewed registry to the complete grouped vocabulary. Registry format
`portable-hosting-capability-registry/2` rejects the former network-only format.
The previous registry is available in Git history, not through a runtime shim.

## Evidence states

`UNASSESSED` means no candidate implementation is asserted.
`DOCUMENTED_EXPECTATION` identifies a documented outcome, not executable support.
`CANDIDATE_SOURCE` means code exists for part of the capability; it does not mean an
integrated workflow has passed. `LOCAL_FIXTURE_ONLY` identifies synthetic or
protocol-fixture coverage. These source states remain independent from native
qualification. Newly enumerated dimensions remain `UNASSESSED` until their
implementation and evidence are reviewed; adding a row does not close a wave.

Every committed platform tuple remains `UNSELECTED`; every capability remains
`NOT_QUALIFIED`. Provider pins and local tests do not qualify installed systems.
The routed IPv6 laboratory remains fixture evidence, not native IPv6 support.

## Eligibility and qualification

A mandatory requirement is satisfied only by a `NATIVE_QUALIFIED` claim for the
selected installed tuple. The validator verifies the current
[native qualification dossier](platform-native-qualification.md), its controlled
evidence references, provenance and current target-bound
[campaign evidence](qualification-campaign-evidence-assurance.md). Editing a flag
or attaching arbitrary evidence is insufficient. Assurance profiles are checked
separately. Native support for one capability never grants other capabilities,
a reverse migration direction or permission to mutate a resource.

The registry validates bounded, duplicate-free JSON and list fields, normalized
repository references and resource-root containment, including symlink escapes.
Malformed, stale, missing or unqualified evidence fails closed. Declared test
inventories cannot authorize production placement.

## Product integration and remaining work

The existing placement and profile resolution components consume these
requirements through `provisioner.repository`. Their existence does not make the
admitted Temporal workflow a complete provisioning or migration workflow. Native
collectors, installed profile persistence, action/directed-route qualification,
guest/service postconditions and recovery acceptance must be completed against
[B14–B50 in the execution plan](../product/enterprise-workload-mobility-execution-plan.md).

Changing a profile requirement changes its reviewed revision and derived plan
identity. Reassess and obtain new approval; do not reinterpret an already approved
plan under the expanded catalogue. Preserve signed historical evidence unchanged.

Run `python -m provisioner.qualification.registry` and the capability,
qualification and family-eligibility tests. These are repository checks and make
no native contact.

[Engineering index](README.md) · [Current RAD](../current/RAD-adoption.md) ·
[Current TAD](../current/TAD-infrastructure.md)
