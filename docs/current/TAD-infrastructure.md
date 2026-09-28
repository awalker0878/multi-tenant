# TAD-M01 — Technical infrastructure composition

**Version:** 0.5 · **Status:** Proposed · **Accountable role:** Platform, network and security engineering.

## Scope and authority

Technical decomposition of the control application, durable authority, discovery, provisioning and migration paths together with fabric, native stacks, security edge and shared services.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §3](../architecture/reference/3-system-context-and-physical-hosting-topology.md) · [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md).

## Design content

The WSD compiler is installed at `provisioner/compiler/wsd.py`, with one native
component map at `provisioner/compiler/components.py`. All callers migrated and
the old executable was deleted without a shim. Compilation depends only on
reviewed package assets and low-level declarations, not build scripts or native
observers. Its JSON input boundary is bounded and rejects ambiguous input before
output creation. Native field shapes, generated resources, disabled outputs and
state keys are preserved; retained execution ownership still requires B05 work.


A commissioned hosting cell provides accepted transport, eligible compute/storage, controlled management and finite attachment/security capacity. The fabric carries the supported underlay and approved physical services; it does not silently federate vendor overlays. Each independent domain instance maps to the chosen VPC, Tier-1/upstream context, Neutron/backend context or qualified physical realization.

All inter-domain transitions have named adjacent authorities and the complete required ZIP functions. Forward/reply routes, NAT/PBR interactions, source identity, policy scope and high-availability behaviour are part of that technical design. Shared EC/SE appliances may support independent logical contexts only with accepted administration, capacity and failure-sharing consequences.

Separate virtual disk I/O, guest file/object access, storage replication, backup transfer and their control planes. Shared service consumption grants only an endpoint/operation/resource scope, not provider administration. Identity, DNS, time, state, keys, backup catalogue and emergency access form a recovery dependency graph which must remain viable for the declared failure.

Native realization must name the actual product/API/provider/feature/entitlement combination. No single provider provisions or qualifies the complete environment. VMware/NSX, Nutanix and OpenStack offer different forwarding and control mechanisms; portability is a demonstrated outcome rather than topology identity.

### Control application and durable authority

`provisioner/controlplane/api` owns authenticated API and portal transport;
`provisioner/cli/operator.py` is a client, not an alternate local controller.
PostgreSQL persistence and row-level security bind business records to authorized
scopes. Immutable plan revisions and their digests survive retries and are checked
against current approvals/revocations before admitting work. Transactional outbox
records avoid treating a successful network dispatch as committed business state.

`provisioner/controlplane/workflow` owns Temporal orchestration. The current
`AdmittedMigrationJob` checks the admitted authority and returns `GATE_PASSED` or a
hold; this is not yet the provisioning/migration graph. Native worker execution
must continue to use durable job/run bindings, resource claims, one-writer intents,
credential boundaries and independent reconciliation. Do not add a direct API-to-
Terraform execution shortcut or equate worker liveness with operation completion.

### Discovery and comparison path

The VMware, AHV and OpenStack discovery adapters are bounded read-only components.
A separate mTLS ingest service validates signed campaign/result identity and native
read-credential witnesses before publication. Original signed bytes and hashes are
retained; ingest and ordinary application SQL roles remain isolated. Publication
locks and generation rechecks prevent stale results from replacing current state.

Installed-tuple, directed-route and control inputs are durable signed records.
Normalization and comparison pin those inputs and the relevant inventory generations;
conflicting/missing VM, disk, NIC, quota and dependency facts do not become confirmed
absence. Duplicate scope declarations cannot create artificial destination diversity.
A comparison is advice, not ownership adoption or an execution grant. Full collector,
profile and credential wiring, persisted owner/dependency review, scheduling and
large-estate qualification remain open.

### Profiles and qualification runtime

`provisioner/domain/capabilities.py` is the sole owner of the 97-dimension vocabulary.
`provisioner/qualification/registry.py` validates complete per-platform declarations;
`provisioner/qualification/native.py` validates current exact-tuple native dossiers.
The full qualification dependency chain is package-owned: `provenance.py`
validates version/source records, `target_selection.py` validates selected native
campaign scope, and `campaign.py` validates target-bound campaign observations.
All five old script entry points were removed and their consumers migrated without
wrappers or import-path mutation. Run the owners using
`python -m provisioner.qualification.<owner>`, where `<owner>` is `registry`,
`native`, `provenance`, `target_selection` or `campaign`. None imports the legacy
scripts/tools packages. Other runtime owners still require relocation; this change
does not close B05.

Registry version 2 binds the vocabulary digest and validates bounded, duplicate-free
JSON, explicit capability rows, controlled evidence links and resource-root
containment. Native-qualified claims require current provenance and target-bound
campaign evidence. Portable compute/storage/recovery/service profiles declare their
own mandatory capabilities; the resolver retains limitations from every selected
profile. A changed catalogue revision invalidates previous derived plan identity
and requires reassessment rather than approval reuse.

### Provisioning and useful-service execution

The lower-level execution code separates native domain/workload provisioning,
private saved Terraform plans, provider task observation, fenced VM lifecycle,
guest configuration and service-owner handoffs. A complete admitted workflow must
compose those effects using exact approved inputs and fresh per-effect authority.
Allocate and confirm capacity, address space and staging budgets transactionally;
keep reservations until independently reconciled release, not until a client exits.

Preserve per-member disk/NIC order, boot/firmware and guest identity. Reject layouts
that cannot be represented or qualified. Native create success must be followed by
independent VM/storage/network/policy observation, approved guest configuration,
DNS/identity/time/trust/logging/monitoring/backup postconditions and controlled
activation. Terraform, native lifecycle code and guest automation must not compete
for the same field or resource writer. Unknown outcomes remain held until observed.

### Migration data plane and recovery

The cross-scope transfer contracts preserve the original source repository/snapshot
identity and signed receipt rather than minting target-side source evidence. Each
dataset has an exact source and target identity, bounded transfer budget, metadata
policy and integrity record. Consistency-group joins require complete declared
dataset coverage. A logical `targetRef` is neither a filesystem path nor a native ID.

Before exposing a mutation path, complete the independently observed target dataset/
root binding, trusted mTLS-worker-to-transfer authority, dynamically scoped native
repository credentials and independent filesystem/old-writer observations. Receipt
validation alone does not implement these integrations. Isolation must suppress
production side effects during rehearsal. Quiesce/fence, final sync, traffic switch,
target write admission, source retention and post-write recovery have separate
approval, evidence and failure boundaries.

### Verification and operating topology

Use the installed wheel outside the checkout to verify resource ownership and imports.
Repository tests exercise profile negatives, all three planning realizations,
authority, signatures, local TLS, database roles and recovery fixtures in their
appropriate CI jobs. The [execution plan](../product/enterprise-workload-mobility-execution-plan.md)
retains unclosed native routes, HA/DR, restore, operating acceptance and release
qualification. Neither a fixture throughput result nor a package build establishes
estate-scale performance, native support or production authorization.

### Typed property and observed migration compatibility

`provisioner/domain/capability_properties.py` owns the property schema, digest,
constraint intersection/implication and conditional realization checks. Resolution
format 3 feeds per-cluster property observations into placement. Policy capsule and
realization format 2 retain source obligations and reject weaker destination plans.
Discovery normalizer 2 retains explicit source requirements and target observed
sets/properties; existing independent signed reviews pin both normalized snapshots.
`discovery/compatibility.py` checks firmware, architecture, secure boot, vTPM state,
encryption layer/keys, shared/passthrough devices, drivers and measured warm-copy
convergence. These are comparison checks, not new native execution paths.
The OpenStack collector whitelists port security/binding/group/QoS/address and
volume encryption/multiattach/type attributes. It never promotes metadata, a
feature flag or a volume type name into an enforced-policy or native support claim.

See [verified research decisions](../engineering/platform-migration-research.md) and
[existing wave-plan delta](../product/enterprise-workload-mobility-execution-plan.md#8-research-driven-acceptance-and-implementation-delta).

### Bounded native hardware observations

AHV VMM v4.0 boot/vTPM and typed disk/NIC facts now enter common discovery pages.
The parser rejects disk-backing union confusion and retains bus/index separately
from array order. VMware REST VM-info contributes CPU, memory, firmware and
whitelisted disk/NIC facts through common campaign pages; folder review identity
and all captured hardware are digest-bound. Visible REST inventory remains partial
and cannot prove absence. Inconclusive reads discard the scan; expired campaigns
cannot issue late evidence. Neither parser ingests native secrets or guest data.

Collector profile revisions require new admitted campaigns and credential witnesses.
The normalizer's existing raw/normalized bindings remain in force. ISA, guest/key
state, application policy, complete controller/boot mappings and deployed transport
remain separate work. A native live-migration hint is not route qualification.
See the [Wave 2 collector follow-up](../product/wave2-discovery-architecture.md#native-hardware-collection-follow-up--28-september-2026).


## Engineering and implementation handoff

The LLD supplies actual native identities, interfaces, addresses, limits, support evidence, privilege scopes and code artifacts. P0–P6 assigns one resource writer per lifecycle scope. Terraform roots, supported installers, service-owner integrations and Ansible procedures consume accepted handoffs without sharing unrestricted credentials.

## Acceptance and open work

Missing native edge construction, platform commissioning, actual IAM/backup/key integrations and tested failure behaviour stay open. Record accepted operation coverage for create/observe/update/adopt/replace/delete and uncertain completion; a valid plan is not a TAD acceptance.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
