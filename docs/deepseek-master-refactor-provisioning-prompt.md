# DeepSeek Master Prompt — Repository Refactor, Parameter-Driven Provisioning, and Documentation Consolidation

> **Repository objective:** Refactor the current multi-tenant hosting repository into a clean, standards-driven, parameterized provisioning system that can accept a portable Workload Security Domain (WSD) / environment request and safely resolve, plan, realize, verify, and operate that request across supported Nutanix, VMware/NSX, and OpenStack environments.
>
> **Execution objective:** Do not merely analyze, plan, scaffold, or document the refactor. Perform the refactor incrementally, preserve valid behavior, migrate active callers, remove superseded code, keep active documentation synchronized, validate continuously, and make small atomic commits throughout.
>
> **Important principle:** Git preserves history. The working tree must represent the current system, not every historical implementation generation.

---

# 0. Operating mode

You are working directly in the current repository.

Operate as a senior infrastructure/platform engineer performing a controlled architectural refactor of an existing codebase with production-oriented safety boundaries.

Your execution loop is:

```text
inspect
→ understand
→ model dependencies
→ implement one coherent increment
→ test
→ update docs
→ migrate callers
→ remove superseded code
→ inspect diff
→ commit
→ rescan
→ continue
```

Do not stop after:

- writing a plan;
- producing a gap analysis;
- creating directories;
- introducing interfaces;
- writing TODOs;
- creating an adapter with no real behavior;
- implementing only one platform;
- implementing code without updating active documentation;
- updating documentation without changing code;
- adding a new path while leaving an obsolete active path beside it;
- creating compatibility shims instead of completing migration;
- creating a new architecture while allowing old current-facing documentation to remain contradictory.

The goal is a **coherent repository**, not a pile of individually correct additions.

---

# 1. End-state definition

The repository must evolve toward a system where an authorized operator, pipeline, service catalogue, or future API supplies a small portable request describing **what environment is needed**, and the platform determines **how to realize it**.

The desired pipeline is:

```text
Portable WSD / Environment Request
             │
             ▼
      Request Normalization
             │
             ▼
    Schema + Semantic Validation
             │
             ▼
       Profile Resolution
             │
             ▼
   Standards / Policy Evaluation
             │
             ▼
 Capability + Qualification Matching
             │
             ▼
 Site / Cell / Platform Placement
             │
             ▼
 Capacity + Resource Reservations
             │
             ▼
 IPAM / DNS / Service Resolution
             │
             ▼
  Canonical Resolved Desired State
             │
             ▼
 Existing WSD Environment Compiler
             │
             ▼
 Platform-Specific Realization
             │
             ▼
 Terraform / Service Owner / Ansible Plan
             │
             ▼
 Approval / Authority Gates
             │
             ▼
 Controlled Execution
             │
             ▼
 Native Observation / Readback
             │
             ▼
 Reconciliation + Verification
             │
             ▼
 Conformance / Evidence
             │
             ▼
 Activation / Ongoing Operations
```

A normal consumer must not need to know provider-native IDs, Terraform module paths, or cluster implementation details.

---

# 2. Required consumer-facing model

The stable consumer-facing contract is the portable WSD / environment intent.

A representative request may resemble:

```yaml
apiVersion: hosting.platform/v1
kind: WorkloadSecurityDomain

metadata:
  tenant: science
  name: research-prod
  owner: science-platform-team

spec:
  environment: production

  security:
    profile: protected-b-medium

  assurance:
    profile: standard

  platform:
    preference: auto

  placement:
    region: east

  availability:
    profile: high

  recovery:
    enabled: true
    profile: standard

  capacity:
    computeProfile: medium
    storageProfile: high-capacity

  zones:
    operations:
      enabled: true

    restricted:
      enabled: true

  services:
    dns: default
    ntp: default
    identity: enterprise
    logging: protected-b
    backup: standard

  exposure:
    publicIngress: false
    internetEgress: false
```

The consumer should not normally supply:

```text
Nutanix cluster IDs
Nutanix VPC IDs
Nutanix subnet IDs
Nutanix storage-container IDs
VMware resource-pool IDs
VMware datastore IDs
vSphere network IDs
NSX segment paths
NSX Tier-1 implementation details
OpenStack project IDs
OpenStack router IDs
OpenStack network IDs
OpenStack subnet IDs
OpenStack security-group IDs
OpenStack availability-zone implementation details
VLAN IDs
VXLAN VNIs
Terraform state keys
Terraform module paths
Ansible inventory implementation details
provider-specific security-policy constructs
```

Those values must be derived from authoritative platform/site/service state.

---

# 3. Existing implementation must be reused, not casually replaced

Before refactoring, inspect the repository deeply.

At minimum inspect:

```text
README.md
docs/**
terraform/**
ansible/**
tools/**
scripts/**
tests/**
examples/**
sources/**
.github/**
```

Pay special attention to existing mechanisms equivalent to:

```text
tools/compile_wsd.py
provisioner/execution/wsd_handoff.py
terraform/stacks/wsd/**
terraform/compositions/**
terraform/modules/**
delivery runner / delivery graph
Terraform saved-plan preparation/application
Ansible guest execution
capacity reservation
OpenStack quota enforcement
IPAM integration
DNS lifecycle
edge activation / containment
native readback
native reconciliation
platform lifecycle
backup / restore
retirement orchestration
drift / health classification
assurance / qualification gates
```

Do not create parallel replacements for mature mechanisms without a concrete reason.

The intended refactor should generally add the missing upper layer:

```text
consumer request
    ↓
profile/policy/placement/allocation
    ↓
resolved hosting environment
    ↓
existing compile_wsd path
    ↓
existing WSD Terraform compositions
    ↓
existing delivery/execution path
```

The refactor must simplify integration around existing proven work rather than discard it.

---

# 4. Refactor goals

The refactor has six equally important goals.

## Goal A — Portable request model

A consumer supplies portable intent rather than platform implementation details.

## Goal B — Deterministic resolution

The system resolves profiles, requirements, placement, service bindings, capacity, and provider realization deterministically.

## Goal C — Platform-native realization

Nutanix, VMware/NSX, and OpenStack use appropriate native constructs while preserving common architectural outcomes.

## Goal D — Clean execution boundaries

Terraform, Ansible, platform APIs, IPAM, DNS, backup, identity, edge/security, and external systems retain explicit ownership.

## Goal E — Repository simplification

The new architecture replaces obsolete active architecture rather than existing beside it indefinitely.

## Goal F — Documentation integrity

Active documentation, code, tests, examples, ADRs, indexes, and backlogs all describe the same current system.

---

# 5. Non-goals

Do not turn the repository into an unnecessary custom cloud-management platform.

Do not rebuild functionality already safely provided by:

- Terraform;
- Ansible;
- platform-native APIs;
- authoritative IPAM;
- authoritative DNS;
- CI/CD;
- external identity systems;
- backup services;
- inventory systems;
- policy engines;
- existing change/approval systems.

Prefer:

```text
small deterministic provisioning core
+
existing execution systems
```

over:

```text
large bespoke orchestration platform
```

unless the repository demonstrates a real requirement for the latter.

---

# 6. Proposed target repository structure

Refactor toward a structure that makes current architecture obvious.

Do not mechanically move files solely to match this example. First map existing code to these responsibilities. Then migrate only where it improves responsibility boundaries and clarity.

Recommended target:

```text
/
├── README.md
├── SECURITY.md
├── CONTRIBUTING.md
│
├── docs/
│   ├── README.md
│   │
│   ├── architecture/
│   │   ├── README.md
│   │   ├── reference/
│   │   ├── security-domains/
│   │   ├── placement/
│   │   ├── networking/
│   │   ├── shared-services/
│   │   ├── lifecycle/
│   │   └── diagrams/
│   │
│   ├── engineering/
│   │   ├── README.md
│   │   ├── provisioning/
│   │   ├── platform-capabilities/
│   │   ├── placement/
│   │   ├── ipam-dns/
│   │   ├── native-readback/
│   │   ├── reconciliation/
│   │   ├── recovery/
│   │   ├── security-edge/
│   │   └── assurance/
│   │
│   ├── implementation/
│   │   ├── README.md
│   │   ├── provisioning/
│   │   ├── terraform/
│   │   ├── ansible/
│   │   ├── delivery/
│   │   ├── operations/
│   │   └── runbooks/
│   │
│   ├── operations/
│   │   ├── README.md
│   │   ├── lifecycle/
│   │   ├── incident/
│   │   ├── recovery/
│   │   └── retirement/
│   │
│   ├── adr/
│   │
│   ├── current/
│   │   └── only truly current maintained material if still needed
│   │
│   ├── archive/
│   │   └── historical/source material only
│   │
│   ├── NEXT_WORK.md
│   └── CHANGELOG.md
│
├── provisioner/
│   ├── __init__.py
│   │
│   ├── domain/
│   │   ├── request.py
│   │   ├── desired_state.py
│   │   ├── placement.py
│   │   ├── lifecycle.py
│   │   ├── evidence.py
│   │   └── errors.py
│   │
│   ├── schemas/
│   │   ├── v1/
│   │   │   ├── workload-security-domain.schema.json
│   │   │   ├── resolved-desired-state.schema.json
│   │   │   ├── placement-decision.schema.json
│   │   │   └── conformance-report.schema.json
│   │   └── registry.py
│   │
│   ├── profiles/
│   │   ├── loader.py
│   │   ├── resolver.py
│   │   └── validation.py
│   │
│   ├── policy/
│   │   ├── semantic.py
│   │   ├── standards.py
│   │   └── diagnostics.py
│   │
│   ├── inventory/
│   │   ├── model.py
│   │   ├── platform.py
│   │   ├── site.py
│   │   ├── service.py
│   │   └── capacity.py
│   │
│   ├── placement/
│   │   ├── eligibility.py
│   │   ├── resolver.py
│   │   ├── scoring.py
│   │   └── decision.py
│   │
│   ├── allocations/
│   │   ├── capacity.py
│   │   ├── ipam.py
│   │   ├── dns.py
│   │   └── reservations.py
│   │
│   ├── services/
│   │   ├── bindings.py
│   │   ├── identity.py
│   │   ├── logging.py
│   │   ├── backup.py
│   │   └── time.py
│   │
│   ├── compiler/
│   │   ├── normalize.py
│   │   ├── profiles.py
│   │   ├── desired_state.py
│   │   ├── environment.py
│   │   └── artifacts.py
│   │
│   ├── adapters/
│   │   ├── base.py
│   │   ├── nutanix/
│   │   ├── vmware/
│   │   └── openstack/
│   │
│   ├── execution/
│   │   ├── plan.py
│   │   ├── delivery.py
│   │   ├── terraform.py
│   │   ├── ansible.py
│   │   └── authority.py
│   │
│   ├── observation/
│   │   ├── native.py
│   │   ├── drift.py
│   │   └── health.py
│   │
│   ├── reconciliation/
│   │   ├── compare.py
│   │   ├── classify.py
│   │   └── decisions.py
│   │
│   ├── conformance/
│   │   ├── checks.py
│   │   ├── report.py
│   │   └── activation.py
│   │
│   └── cli/
│       ├── main.py
│       ├── validate.py
│       ├── resolve.py
│       ├── plan.py
│       ├── apply.py
│       ├── status.py
│       ├── verify.py
│       └── evidence.py
│
├── profiles/
│   ├── security/
│   ├── assurance/
│   ├── availability/
│   ├── recovery/
│   ├── compute/
│   ├── storage/
│   ├── network/
│   ├── service/
│   ├── placement/
│   └── environment/
│
├── policy/
│   ├── README.md
│   ├── rules/
│   └── tests/
│
├── inventory/
│   ├── README.md
│   ├── schema/
│   └── fixtures/
│
├── terraform/
│   ├── README.md
│   ├── modules/
│   │   ├── nutanix/
│   │   ├── vmware/
│   │   ├── openstack/
│   │   └── shared/
│   │
│   ├── compositions/
│   │   ├── nutanix/
│   │   ├── vmware/
│   │   └── openstack/
│   │
│   ├── stacks/
│   │   ├── components/
│   │   └── wsd/
│   │       ├── nutanix/
│   │       ├── vmware/
│   │       └── openstack/
│   │
│   ├── catalog.json
│   └── tests/
│
├── ansible/
│   ├── README.md
│   ├── roles/
│   ├── playbooks/
│   ├── inventory/
│   ├── templates/
│   └── tests/
│
├── tools/
│   ├── native/
│   ├── owners/
│   ├── migration/
│   └── compatibility/
│       └── ideally empty at end of refactor
│
├── scripts/
│   ├── validation/
│   ├── assurance/
│   ├── documentation/
│   └── maintenance/
│
├── examples/
│   ├── requests/
│   ├── resolved/
│   ├── environments/
│   ├── fixtures/
│   └── golden/
│
├── tests/
│   ├── unit/
│   ├── schema/
│   ├── policy/
│   ├── placement/
│   ├── compiler/
│   ├── adapters/
│   ├── terraform/
│   ├── ansible/
│   ├── delivery/
│   ├── reconciliation/
│   ├── conformance/
│   ├── documentation/
│   └── end_to_end/
│
├── sources/
│   ├── capabilities/
│   ├── assurance/
│   ├── implementation/
│   └── historical/
│
└── .github/
    └── workflows/
```

## Structure rules

The final structure must make these boundaries obvious:

```text
portable intent
≠
resolved desired state
≠
platform realization
≠
execution
≠
observation
≠
authorization
```

Do not mix these concerns.

---

# 7. Refactor before feature expansion

The repository should not keep accumulating code around unclear existing boundaries.

Before implementing major new features:

1. map current code to target responsibilities;
2. identify duplicate responsibilities;
3. identify obsolete paths;
4. identify active paths that must remain stable during migration;
5. introduce the new boundaries incrementally;
6. migrate callers;
7. delete superseded paths.

Do not attempt a single giant directory move.

Perform the refactor in controlled slices.

---

# 8. Refactor migration strategy

Use the following migration phases.

---

## Phase R0 — Repository inventory and dependency map

Create an internal implementation inventory.

Do not stop after creating it.

Identify:

```text
current entry points
active CLI/tools
request/config formats
compiler paths
Terraform compositions
Terraform roots
Ansible execution paths
delivery coordination
service-owner adapters
native observers
reconciliation paths
test fixtures
examples
documentation references
```

For each significant component record internally:

```text
responsibility
current path
callers
inputs
outputs
owner
replacement target
migration status
```

Search for likely legacy indicators:

```text
legacy
deprecated
compat
old
previous
temporary
migration
shim
fallback
v0
v1
TODO
FIXME
TBD
obsolete
superseded
```

Classify every significant occurrence as:

```text
CURRENT_REQUIRED
HISTORICAL_ONLY
TEMPORARY_MIGRATION
OBSOLETE
```

Do not infer solely from filenames.

Inspect actual reachability.

---

## Phase R1 — Establish authoritative current entry points

Identify and document the canonical current path.

For example:

```text
consumer request
→ provisioner core
→ resolved environment
→ existing WSD compiler
→ Terraform stacks
→ delivery runner
→ observation
→ verification
```

Update the main README and active implementation index so there is exactly one clear path.

Do not move implementation yet unless needed.

This phase creates clarity before movement.

---

## Phase R2 — Introduce the `provisioner/` package

Create the portable provisioning core.

Do not implement empty abstractions.

Start with a vertical slice:

```text
request load
→ normalize
→ schema validation
→ semantic validation
→ resolved request
```

Immediately add tests.

Recommended initial interfaces:

```python
validate(request)
normalize(request)
resolve_profiles(request, catalogs)
resolve_placement(request, inventory)
compile_environment(resolved)
plan(request)
```

Use strong data models or equivalent validation.

Do not leak platform-specific fields upward.

---

## Phase R3 — Canonical request contract

Create the active machine-readable request schema.

Requirements:

- versioned;
- closed property sets where practical;
- explicit optionality;
- explicit enums;
- clear validation diagnostics;
- vendor-neutral;
- portable;
- no secret values;
- no provider-native IDs in normal consumer fields.

Migrate all current example requests to the new format.

If an older active request format exists:

1. find every caller;
2. migrate callers;
3. migrate tests;
4. migrate examples;
5. migrate docs;
6. delete the old active reader.

Do not preserve two active contracts without an explicit compatibility requirement.

---

## Phase R4 — Profile consolidation

Create or consolidate versioned profile catalogs.

Minimum profile domains:

```text
security
assurance
environment
availability
recovery
compute
storage
network
service
placement
```

Each profile must have:

```text
id
version
description
requirements
defaults
constraints
```

Profile resolution must output explicit values.

Example:

```yaml
profile:
  id: compute-medium
  version: 1

resolved:
  vcpu: 16
  memoryGiB: 64
```

Do not hide important implementation behavior in undocumented Python constants if it is genuinely policy/profile data.

---

## Phase R5 — Semantic policy engine

Implement policy that cannot be represented by schema alone.

Examples:

```text
production environment requires an allowed recovery profile
public ingress requires an implemented public/PAZ service profile
unsupported zones fail
unsupported IPv6 mode fails
cross-tenant references fail
platform override must satisfy mandatory capabilities
recovery placement cannot equal prohibited failure domain
service binding must be available for selected security profile
invalid zone transitions fail
```

Diagnostics must identify:

```text
rule
field
expected outcome
actual request
```

Do not silently rewrite unsafe requests.

---

## Phase R6 — Inventory abstraction

Separate portable request processing from actual site/platform data.

Create a canonical inventory abstraction representing:

```text
site
cell
platform family
installed tuple
qualification state
service classes
zones
capacity
storage profiles
network capabilities
recovery capabilities
location constraints
tenant eligibility
service bindings
```

The inventory layer may consume existing files, future APIs, or exported authoritative records.

The provisioning core must not depend on Git-hosted fixture files as if they were production inventory.

Fixtures are test inputs only.

---

## Phase R7 — Placement engine

Implement deterministic placement.

Input:

```text
resolved requirements
qualified capability registry
current inventory
capacity state
tenant eligibility
recovery constraints
location constraints
```

Output:

```yaml
decision:
  platform: nutanix
  site: east-01
  cell: cell-03
  serviceClass: protected-standard

reasons:
  - qualified for required capabilities
  - sufficient surviving capacity
  - tenant eligible
  - recovery target available

rejectedCandidates:
  - candidate: vmware-central-02
    reasons:
      - recovery profile unavailable
```

No arbitrary iteration-order selection.

Add deterministic tie-breaking.

Add tests for:

```text
one candidate
multiple candidates
no candidates
explicit platform
platform:auto
capacity shortage
qualification mismatch
security mismatch
region mismatch
recovery mismatch
tenant ineligible
```

---

## Phase R8 — Capacity and reservation integration

Integrate placement with the existing authoritative reservation mechanisms.

Placement alone does not reserve.

Model:

```text
candidate placement
→ reservation request
→ reservation confirmed
→ allocation bound to generation
```

Do not pretend capacity exists simply because static inventory lists it.

Uncertain reservation outcomes must stop and reconcile.

---

## Phase R9 — IPAM and network allocation

The consumer requests network intent, not CIDRs.

Resolve:

```text
zone
prefix size
address family
service class
site
tenant
WSD
```

through the authoritative IPAM handoff.

Do not let Terraform invent unique network allocations independently.

Support:

```text
reserve
confirm
observe
reconcile
retire
```

according to existing ownership contracts.

---

## Phase R10 — Shared-service resolution

Resolve portable service requests:

```yaml
services:
  dns: default
  ntp: default
  identity: enterprise
  logging: protected-b
  backup: standard
```

to site/platform-specific service bindings.

Each binding should contain only the minimum handoff needed by downstream implementation.

Do not expose another service's administrative state unnecessarily.

---

## Phase R11 — Compile resolved intent into the existing environment model

The new upper-layer compiler should generate the existing environment contract consumed by `compile_wsd.py`, unless that contract itself is intentionally superseded through a separate migration.

The target relationship is:

```text
portable request
→ resolved desired state
→ hosting-wsd-environment
→ compile_wsd
→ Terraform WSD compositions
```

Do not bypass a mature validation path without reason.

If the existing environment contract contains provider-specific details, that is acceptable because it is an **internal compiler boundary**, not the consumer API.

---

## Phase R12 — Existing compiler modernization

Refactor `compile_wsd.py` only where necessary to make it a clean internal compiler boundary.

Potential actions:

- move reusable functions into `provisioner/compiler/environment.py`;
- preserve a thin CLI wrapper if still useful;
- centralize duplicated validation;
- improve typed errors;
- remove provider-specific logic that belongs in adapters;
- maintain exact output behavior during migration.

Do not break current tests casually.

Where behavior intentionally changes, update tests and docs together.

---

## Phase R13 — Platform adapter boundaries

Define a clean adapter contract.

Conceptually:

```python
class PlatformAdapter:
    def validate_capabilities(...)
    def compile_domains(...)
    def compile_workloads(...)
    def required_native_inputs(...)
    def expected_outputs(...)
```

Do not create empty base classes without migrating real behavior.

Move provider-specific logic from generic compiler code only when it improves separation.

Adapters:

```text
Nutanix
VMware/NSX
OpenStack
```

must preserve provider-native strengths.

---

## Phase R14 — Terraform structure cleanup

Map current Terraform directories to:

```text
modules
compositions
stacks/components
stacks/wsd
```

Keep one active realization path per responsibility.

Delete:

```text
duplicate roots
superseded compositions
unused variables
unused outputs
orphan modules
obsolete examples
unused wrappers
```

only after confirming migration.

For each Terraform root maintain:

```text
owner scope
state scope
input contract
output contract
authority boundary
lifecycle responsibility
```

Prefer machine-readable catalog metadata.

---

## Phase R15 — Ansible structure cleanup

Clarify Ansible ownership.

Ansible should configure resources after infrastructure ownership is established.

Do not allow Terraform and Ansible to manage the same configuration field without explicit design.

Organize by:

```text
roles
playbooks
inventory generation
templates
validation
```

Remove abandoned roles/playbooks after migrating active callers.

---

## Phase R16 — Delivery integration

The new provisioning `plan` must produce inputs for the existing delivery graph.

Do not create a second orchestration engine.

Plan output should identify:

```text
Terraform scopes
service-owner operations
guest configuration
verification steps
activation prerequisites
```

Execution must use existing approval, fencing, durable attempt, and recovery behavior.

---

## Phase R17 — Native observation and reconciliation

Preserve the rule:

```text
Terraform state != native truth
```

After execution:

```text
read native state
compare requested / desired / observed
classify differences
```

Never blindly retry uncertain mutations.

Maintain:

```text
attempt identity
generation
writer fencing
containment state
native task identity
observation freshness
```

---

## Phase R18 — Conformance engine

Create a canonical conformance result.

Example:

```yaml
conformance:
  isolation:
    status: pass

  encryption:
    status: pass

  identity:
    status: pass

  logging:
    status: pass

  backup:
    status: pass

  recovery:
    status: pass

  placement:
    status: pass

overall:
  status: pass
```

Mandatory failures block activation.

Unknown required evidence must not become PASS.

---

## Phase R19 — CLI consolidation

Create a coherent CLI.

Target:

```bash
hosting validate request.yaml
hosting resolve request.yaml
hosting plan request.yaml
hosting apply request.yaml
hosting status <wsd>
hosting verify <wsd>
hosting evidence <wsd>
```

Future lifecycle:

```bash
hosting update <wsd>
hosting contain <wsd>
hosting recover <wsd>
hosting retire <wsd>
```

The CLI is a transport/interface.

Business logic belongs in reusable modules.

Remove old user-facing CLI entry points after migration unless they represent separate owner tools with distinct authority.

---

## Phase R20 — End-to-end golden paths

Build real vertical reference paths.

At minimum:

```text
internal development WSD
internal production WSD
OZ/RZ multi-tier WSD
recovery-enabled WSD
storage-heavy/archive WSD
```

Each should compile across all compatible platforms.

Do not claim:

```text
PAZ/public
IPv6-only
dual-stack
higher assurance
bare metal
container hosting
GPU
```

until their required implementation is genuinely delivered.

Unsupported request types must fail clearly.

---

# 9. Documentation authority model

Documentation must have explicit authority.

Use this model.

## Tier 1 — Active architecture

```text
docs/architecture/**
```

Defines current infrastructure architecture.

## Tier 2 — Active engineering

```text
docs/engineering/**
```

Defines current technical realization rules and boundaries.

## Tier 3 — Active implementation

```text
docs/implementation/**
```

Defines current repository implementation and operator procedures.

## Tier 4 — ADRs

```text
docs/adr/**
```

Records decisions and supersession relationships.

## Tier 5 — Historical/source material

```text
docs/archive/**
```

Preserves history and provenance only.

Archived material is never automatically authoritative.

## Tier 6 — Remaining work

```text
docs/NEXT_WORK.md
sources/implementation_backlog.csv
```

Contains genuinely unresolved items only.

Do not allow completed tasks to remain described as active gaps.

---

# 10. Documentation refactor rules

For every implementation change ask:

```text
Which architecture document describes this?
Which engineering document describes this?
Which implementation/runbook describes this?
Which examples use this?
Which code map links this?
Which backlog item is affected?
Which ADR is affected?
```

Update them in the same logical change where practical.

Do not create documentation duplicates.

Prefer one authoritative current document and links from other places.

---

# 11. Archive rules

Historical material may remain only when it has value for:

```text
source provenance
audit trail
previous release understanding
superseded architecture reference
```

Every historical area must clearly state:

```text
HISTORICAL — NOT CURRENT IMPLEMENTATION GUIDANCE
```

Do not use archived documents as implementation instructions unless an active document explicitly references a still-valid requirement.

When search results find an old design in `docs/archive`, do not blindly reimplement it.

---

# 12. Legacy-code removal standard

The refactor is incomplete while old and new active implementations coexist without a supported compatibility requirement.

For every replaced implementation:

```text
1. identify all callers
2. migrate callers
3. migrate tests
4. migrate examples
5. migrate CI
6. migrate docs
7. delete obsolete code
8. repository-wide search for old symbol/path
9. run tests
10. commit
```

Do not skip deletion.

Git is the rollback/history mechanism.

---

# 13. Compatibility policy

Compatibility is allowed only if there is a real consumer that cannot yet migrate.

Any compatibility layer must include:

```text
consumer
reason
migration path
removal condition
owner
```

Prefer placing temporary compatibility code in:

```text
tools/compatibility/
```

so it is visibly temporary.

At the end of the refactor this directory should ideally be empty.

Do not preserve compatibility merely because old tests exist.

---

# 14. No dead-code exception for tests

Tests are not justification for legacy architecture.

If a test protects behavior that is intentionally removed:

```text
remove/update the test
remove the legacy implementation
```

Tests protect intended current behavior.

---

# 15. Schema migration policy

When changing a schema:

1. define the target schema;
2. migrate active examples;
3. migrate active tools;
4. migrate tests;
5. migrate pipelines;
6. migrate docs;
7. remove obsolete readers;
8. remove obsolete schema files.

If multiple schema versions are intentionally supported, maintain an explicit compatibility matrix:

```text
version
status
supported until
migration path
```

Do not let old schema support remain accidental.

---

# 16. Terminology migration

When terminology changes, perform a repository-wide migration.

Examples:

```text
old environment model
→ WSD desired state

department
→ tenant

legacy zone label
→ current security-domain vocabulary
```

Classify every occurrence:

```text
CURRENT_MUST_CHANGE
HISTORICAL_KEEP
```

Do not leave mixed current terminology.

---

# 17. Code ownership boundaries

Every resource/configuration class must have one primary owner.

Maintain or create a machine-readable ownership map.

Examples:

```text
physical fabric → foundation/network owner
hypervisor cluster → platform owner
tenant WSD network → Terraform platform composition
guest OS configuration → Ansible
IP address → authoritative IPAM
DNS record → DNS service owner
edge policy → security-edge owner
backup policy → backup owner
identity/certificate → identity/trust owner
```

Do not allow overlapping ownership.

---

# 18. Terraform standards

For every module/composition/root:

- run `terraform fmt`;
- validate configuration;
- use explicit variable types;
- validate required constraints;
- avoid undocumented defaults that weaken security;
- expose only required outputs;
- never output secrets;
- avoid hidden provider-side behavior when architecture requires explicit control;
- use stable `for_each` keys;
- preserve state ownership;
- avoid one giant root.

Modules should implement native realization.

Business policy should be resolved before reaching low-level provider modules wherever practical.

---

# 19. Ansible standards

Require:

- idempotence;
- deterministic inventory;
- explicit variables;
- no hidden ambient SSH configuration;
- safe check mode where meaningful;
- bounded privilege;
- reproducible templates;
- no duplicated ownership with Terraform;
- meaningful failure diagnostics.

Test syntax and idempotence where possible.

---

# 20. Request validation standards

Validation has layers.

## Layer 1 — Syntax/schema

Field names, types, enums, required fields.

## Layer 2 — Structural semantics

Examples:

```text
recovery profile required when recovery enabled
zone references must exist
flow endpoints must exist
```

## Layer 3 — Standards policy

Examples:

```text
security profile permits requested exposure
environment permits requested assurance level
service binding permitted
```

## Layer 4 — Capability eligibility

Examples:

```text
platform can provide required networking
platform supports requested recovery profile
```

## Layer 5 — Current inventory/capacity

Examples:

```text
eligible cell exists
capacity available
```

Do not collapse all failures into generic "invalid request".

Return actionable diagnostics.

---

# 21. Placement requirements

Placement must satisfy all mandatory constraints.

A candidate should be rejected when any mandatory requirement fails.

Never use a weighted score to override a failed mandatory requirement.

The process should be:

```text
filter mandatory eligibility
→ deterministic preference/tie-break among valid candidates
```

Potential mandatory dimensions:

```text
security
assurance
service class
region/location
platform qualification
address family
network capability
storage
keys/KMS
backup
recovery
availability
surviving capacity
tenant eligibility
```

---

# 22. Platform:auto requirements

`platform:auto` must be real.

It must not mean:

```text
choose Nutanix by default
```

or:

```text
choose first dictionary entry
```

It means:

```text
evaluate all current eligible qualified candidates
→ reject incompatible candidates
→ deterministically choose among remaining candidates
```

Record rejected-candidate reasons for review.

---

# 23. Platform-specific override

Allow:

```yaml
platform:
  preference: nutanix
```

or equivalent.

But an explicit platform must still satisfy mandatory requirements.

Never treat explicit provider selection as permission to weaken standards.

---

# 24. Internal compiler contract

After resolution, generate a complete internal environment object.

Example conceptually:

```yaml
format: hosting-wsd-environment/1

environment_key: research-prod
site_key: east-01
platform: nutanix
lifecycle: production

clusters:
  - id: workload-cell-03
    role: workload
    zone: OZ
    ...

wsds:
  - tenant_key: science
    wsd_key: research-prod
    trust: protected-b
    service_class: standard
    domains:
      ...
```

This internal object may contain platform implementation details.

The consumer request must not.

---

# 25. Desired-state artifact requirements

Generate a canonical desired-state representation before Terraform realization.

It should capture:

```text
request identity
generation
resolved profile versions
placement
logical domains
selected domain instances
networks
flows
service bindings
capacity allocations
recovery
security requirements
platform adapter
```

This artifact becomes the stable bridge between portable policy and provider realization.

---

# 26. Generated artifact integrity

Generated artifacts must include digests or equivalent immutable binding.

At minimum bind:

```text
request digest
resolved profile versions
inventory snapshot/reference
placement decision
desired-state digest
generation
```

Execution must be able to prove it is applying the reviewed plan for the same desired state.

---

# 27. Plan requirements

`hosting plan` must show enough information for a reviewer to understand consequences.

Include:

```text
request summary
resolved profiles
policy decisions
platform/site/cell
capacity/reservations
network/IPAM intent
service bindings
Terraform scopes
Ansible scopes
security changes
recovery changes
external-owner operations
verification requirements
destructive/disruptive classification
activation prerequisites
```

Plan output must not contain secrets.

---

# 28. Apply requirements

Apply must not recompute an unreviewed plan and blindly execute it.

Prefer:

```text
prepare immutable plan
→ review/approve
→ apply exact plan
```

Preserve existing saved-plan and digest-binding behavior.

---

# 29. Generation model

Each WSD must have stable identity and monotonic generation.

Conceptually:

```text
WSD: research-prod
generation: 12
```

A changed desired state increments generation.

Track:

```text
request digest
desired-state digest
placement decision
execution plan digest
observed generation
verification state
```

---

# 30. Idempotence

Same WSD + same generation + same desired-state digest must not create duplicate resources.

Add tests for replay.

Do not rely solely on Terraform idempotence when external-owner operations are involved.

---

# 31. Concurrency

Assume many WSDs provision concurrently.

Protect:

```text
capacity
IPAM
DNS ownership
state
reservation IDs
WSD identity
shared service allocations
```

Use authoritative locking/reservations.

Do not depend on local filesystem ordering for production semantics.

---

# 32. Failure model

Treat external mutations as uncertain when response is lost.

Never assume:

```text
timeout == failure
```

Required response:

```text
hold
→ observe
→ reconcile
→ decide
```

No automatic duplicate mutation.

---

# 33. Native observation

For every important resource define:

```text
expected native identity
expected generation
observable fields
freshness
unknown behavior
```

A successful Terraform apply is not sufficient native evidence.

---

# 34. Drift behavior

Classify drift.

Recommended categories:

```text
EXPECTED
BENIGN
CORRECTABLE
APPROVED_EMERGENCY
SECURITY_SIGNIFICANT
UNKNOWN
```

Do not automatically erase approved emergency controls.

Unknown security-relevant drift should fail closed.

---

# 35. Containment

Incident containment outranks routine reconciliation.

Do not allow ordinary apply/reconcile logic to remove active containment.

Containment release requires its own authority.

---

# 36. Recovery

Recovery is a first-class profile.

Resolve:

```text
recovery site/cell
required capacity
network reconstruction
service dependencies
data protection
key dependencies
activation process
```

Do not bolt recovery onto a provisioned workload afterward.

---

# 37. Retirement

Retirement must be dependency-aware.

Required ordering may include:

```text
withdraw exposure
stop workloads
retain required evidence/data
remove service bindings
release DNS
release IPAM
release capacity
retire native resources
sanitize according to policy
close state/ownership records
```

Do not release reusable resources before dependent state is safely removed.

---

# 38. Evidence

Evidence must remain scoped and attributable.

Associate with:

```text
tenant
WSD
generation
site
platform
service class
operation
```

Do not mix:

```text
local fixture
provider mock
native observation
formal qualification
production authorization
```

as if they are equivalent.

---

# 39. Production activation

Activation is separate from:

```text
Terraform success
Ansible success
delivery graph completion
```

Activation requires:

```text
mandatory conformance PASS
required native evidence
required operational readiness
required authority
```

If required post-activation verification fails, use the defined withdrawal/containment process.

---

# 40. Current supported-service truthfulness

Do not claim support because architecture text exists.

Maintain a machine-readable support matrix.

Example:

```yaml
serviceProfiles:

  internal-ipv4-oz-rz:
    status: IMPLEMENTED

  public-paz:
    status: NOT_IMPLEMENTED

  dual-stack:
    status: NOT_IMPLEMENTED

  ipv6-only:
    status: NOT_IMPLEMENTED
```

Requests for unsupported profiles must fail clearly.

As capabilities are completed, update this matrix and active docs in the same change.

---

# 41. Cross-platform parity definition

Parity does not mean same native resource graph.

Parity means the same portable requirement receives equivalent architectural outcomes.

Test:

```text
isolation
security policy
availability
recovery
logging
backup
identity
service binding
```

across compatible platforms.

---

# 42. Golden contract tests

Create golden portable requests.

For each request:

```text
request
→ normalized request
→ resolved profiles
→ placement fixtures
→ desired state
→ platform realization
```

Store deterministic expected outputs.

Avoid brittle fields such as timestamps in golden comparisons.

---

# 43. Test organization

Refactor tests into clear categories:

```text
tests/unit
tests/schema
tests/policy
tests/placement
tests/compiler
tests/adapters
tests/terraform
tests/ansible
tests/delivery
tests/reconciliation
tests/conformance
tests/documentation
tests/end_to_end
```

Migrate old tests gradually.

Do not duplicate every test during migration.

Move or rewrite, then delete old copies.

---

# 44. CI gates

CI should ultimately enforce:

```text
Python/unit tests
schema tests
policy tests
placement tests
compiler tests
Terraform format
Terraform validate
plan-only provider mocks
Ansible syntax
Ansible idempotence/check-mode where practical
documentation links
stale-path checks
deprecated-interface checks
generated artifact consistency
security scans already supported by repository
```

Do not let CI invoke production infrastructure.

---

# 45. Documentation drift checks

Add checks that fail when active docs reference:

```text
deleted files
removed commands
removed schema names
retired directory paths
explicitly forbidden legacy terms
```

Maintain a small machine-readable list of retired interfaces if useful.

Example:

```yaml
retiredInterfaces:
  - tools/old_compile.py
  - hosting-wsd-request/0
  - terraform/legacy/
```

CI should reject reintroduction unless intentionally changed.

---

# 46. Dependency direction rules

Enforce dependency direction.

Recommended:

```text
domain
↑
profiles / policy / inventory
↑
placement / allocations / services
↑
compiler
↑
adapters
↑
execution / CLI
```

Provider adapters may depend on the domain model.

The domain model must not depend on provider adapters.

CLI must not contain core logic.

Tests should verify imports or architecture boundaries where practical.

---

# 47. No circular ownership

Examples of forbidden design:

```text
Terraform creates DNS
while DNS owner independently creates DNS

Ansible configures firewall
while Terraform owns same firewall rules

placement engine mutates capacity
while reservation service owns capacity
```

Resolve ownership explicitly.

---

# 48. Error model

Create structured errors.

Examples:

```text
SchemaError
SemanticValidationError
PolicyViolation
NoEligiblePlatform
NoEligibleSite
InsufficientCapacity
AllocationConflict
UnsupportedServiceProfile
ExternalAuthorityRequired
UncertainOperation
NativeReconciliationRequired
```

CLI output should be useful to humans while library callers can inspect structured data.

---

# 49. Logging

Do not log secrets.

Use structured operation identifiers.

Include:

```text
request ID
WSD
generation
operation ID
step
```

where appropriate.

Do not copy opaque native error bodies into untrusted logs when existing security boundaries prohibit that.

---

# 50. Secrets

Never store secrets in:

```text
Git
request YAML
desired-state artifacts
tfvars
plan summaries
evidence bundles
logs
```

Use secret references or approved runtime injection.

---

# 51. Repository cleanliness

Delete:

```text
generated local files
temporary migration artifacts
debug dumps
unused scripts
abandoned experiments
duplicate documentation
```

Do not commit tool caches or live state.

---

# 52. Refactor commit discipline

Make small commits.

Good examples:

```text
refactor(provisioner): introduce canonical domain models

feat(schema): add portable WSD v1 request contract

feat(profiles): resolve compute storage and environment profiles

feat(policy): enforce portable WSD semantic rules

feat(placement): add qualified platform filtering

feat(placement): add deterministic site and cell selection

refactor(compiler): isolate environment compilation behind provisioner

refactor(terraform): remove superseded WSD root wrapper

refactor(ansible): consolidate generated guest inventory path

feat(cli): add hosting validate

feat(cli): add hosting plan

test(contract): add cross-platform golden WSD fixtures

docs(provisioning): replace legacy request workflow

chore(cleanup): remove obsolete request schema and tests
```

Avoid giant "refactor everything" commits.

---

# 53. Commit completion checklist

Before every commit:

```text
[ ] implementation is coherent
[ ] relevant tests pass
[ ] docs changed if behavior changed
[ ] examples changed if interface changed
[ ] old caller migrated
[ ] no accidental secrets
[ ] diff inspected
[ ] no unrelated generated files
```

Then commit.

---

# 54. Major-milestone cleanup commit

After each migration phase perform a cleanup pass.

Search:

```text
old symbol
old path
old schema
old terminology
legacy
deprecated
compat
TODO
FIXME
```

Remove obsolete leftovers.

Use a separate cleanup commit if substantial.

---

# 55. Documentation update strategy

Do not create a new document for every small change.

Prefer maintaining authoritative docs.

For provisioning, converge toward a compact active set such as:

```text
docs/architecture/reference/provisioning.md
docs/engineering/provisioning/request-contract.md
docs/engineering/provisioning/profile-model.md
docs/engineering/provisioning/placement.md
docs/engineering/provisioning/desired-state.md
docs/implementation/provisioning/cli.md
docs/implementation/provisioning/delivery.md
docs/implementation/provisioning/platform-adapters.md
docs/operations/lifecycle/wsd-lifecycle.md
```

Adapt names to existing repository conventions.

---

# 56. Documentation retirement

When a new active doc replaces an old active doc:

```text
1. migrate unique useful content
2. update incoming links
3. remove old active doc
or
4. move it to archive with HISTORICAL marker
```

Do not keep both as active guidance.

---

# 57. README requirements

The root README must answer:

```text
What is this repository?
What is the current supported provisioning path?
What is implemented?
What remains unqualified?
Where are architecture docs?
Where are implementation docs?
How do I run local validation?
```

Do not let it become a chronological changelog.

---

# 58. NEXT_WORK requirements

`docs/NEXT_WORK.md` must contain only genuine remaining work.

Each item should identify:

```text
gap
why it matters
dependency
completion condition
external vs repository-side status
```

When completed, remove or mark completed and move durable content elsewhere.

Do not let NEXT_WORK become a history file.

Git is history.

---

# 59. ADR requirements

Use ADRs only for real architectural decisions.

When superseding:

```text
old ADR status: superseded
replacement ADR: linked
active docs: updated
```

Do not rewrite history silently.

---

# 60. Migration safety

Refactoring code does not authorize live resource migration.

If Terraform addresses change:

```text
document required state mv/import procedure
do not automatically destroy/recreate
```

Source refactor and live infrastructure migration are separate concerns.

Maintain `prevent_destroy` and ownership safeguards as required.

---

# 61. Provider state boundaries

Keep state scoped.

Do not create a universal shared state containing:

```text
all tenants
all service owners
all credentials
```

Preserve bounded ownership and blast radius.

---

# 62. Platform adapter contract tests

Each adapter must pass contract tests.

Examples:

```text
required zones represented
required isolation represented
network intent preserved
service bindings preserved
placement references preserved
recovery intent preserved
unsupported capability rejected
```

The tests should not assume identical native implementation.

---

# 63. Platform-specific implementation standards

## Nutanix

Preserve appropriate native:

```text
cluster placement
storage container
subnet/VPC constructs
security categories/policy
quarantine
Flow lifecycle
```

## VMware/NSX

Preserve appropriate:

```text
resource pools
datastores
vSphere VM placement
NSX segments
gateway/DFW policy
network binding verification
```

## OpenStack

Preserve appropriate:

```text
project scope
networks/subnets
security groups
routers
Nova placement
Cinder
quotas
```

Do not leak these concepts into portable consumer requests.

---

# 64. Internal IPv4 OZ/RZ first

Complete the strongest existing portable path first.

Target:

```text
Internal IPv4
OZ/RZ
Nutanix
VMware/NSX
OpenStack
```

Make this path complete before broadening to every advanced service class.

---

# 65. Advanced profiles later

Treat these as explicit extensions until fully implemented:

```text
PAZ/public hosting
dual-stack
IPv6-only
higher assurance
bare metal
container/Kubernetes hosting
GPU/accelerator
cross-stack patterns
L2 stretch
```

Do not let extension design contaminate the core path prematurely.

---

# 66. Service-catalog readiness

Core provisioning must be transport-independent.

A future interface may be:

```text
CLI
REST
GitOps
service portal
workflow engine
```

Do not make core logic depend on terminal interaction.

---

# 67. Suggested library API

Aim for a reusable API such as:

```python
validate_request(request)
normalize_request(request)
resolve_request(request, profiles, policy)
place_request(resolved, inventory)
allocate_request(placement, authorities)
compile_desired_state(...)
compile_environment(...)
create_plan(...)
execute_plan(...)
observe(...)
verify(...)
```

Actual names may differ.

Keep functions small and deterministic where possible.

---

# 68. Pure-function preference

Use pure deterministic functions for:

```text
normalization
profile resolution
policy evaluation
candidate filtering
desired-state generation
```

Separate mutation-heavy operations:

```text
reservations
IPAM
DNS
Terraform apply
Ansible execution
native APIs
```

This improves testability and safety.

---

# 69. External authority adapters

Model external systems behind narrow interfaces.

Examples:

```text
CapacityAuthority
IpamAuthority
DnsAuthority
IdentityAuthority
BackupAuthority
EdgeAuthority
```

Do not build fake production implementations.

Use fixtures/mocks for tests.

---

# 70. Test fixture separation

Clearly separate:

```text
examples
test fixtures
native evidence
production inputs
```

Do not accidentally treat example data as current inventory.

---

# 71. Deterministic generated output

Generated plans/artifacts should be deterministic from the same inputs where possible.

Sort maps/lists where semantic order is irrelevant.

Avoid timestamps in deterministic artifacts unless explicitly part of the record.

---

# 72. File naming

Use stable, descriptive names.

Avoid:

```text
new2.py
final.py
final-final.py
legacy_fix.py
tmp_compiler.py
```

Refactor cleanly into final paths.

---

# 73. No hidden feature flags for permanent architecture

Temporary feature flags may assist migration, but they must have an exit plan.

Do not keep:

```text
USE_NEW_COMPILER
USE_LEGACY_COMPILER
```

forever.

Complete migration and delete the flag.

---

# 74. No duplicate source of truth

Examples of unacceptable duplication:

```text
capabilities in Python constants
and
capabilities in JSON
with no generated relationship

profile values in docs
and
different profile values in code

Terraform root list in README
and
different root list in catalog
```

Choose an authoritative machine-readable source and generate/validate secondary representations where practical.

---

# 75. Generated indexes

Where practical generate:

```text
Terraform root catalog
CLI command reference
supported-service matrix
profile index
documentation index
```

from authoritative sources.

Do not manually maintain multiple inconsistent lists.

---

# 76. Security defaults

Default behavior must remain fail-closed.

Examples:

```text
no public exposure unless explicitly requested and supported
no cross-zone flow without explicit declaration
no activation without verification
no unknown placement
no unsupported capability downgrade
no automatic retry after uncertain mutation
```

---

# 77. Validation of unsupported requests

A good rejection is a feature.

Examples:

```text
UNSUPPORTED_PUBLIC_PROFILE
NO_NATIVE_IPV6_QUALIFICATION
NO_ELIGIBLE_RECOVERY_CELL
NO_QUALIFIED_PLATFORM
INSUFFICIENT_CAPACITY
```

Return precise blockers.

---

# 78. End-to-end reference command

The target command is:

```bash
hosting plan examples/requests/internal-production.yaml
```

The plan should derive:

```text
tenant
WSD
profiles
policy
platform
site
cell
domain placement
service bindings
capacity reservation requirements
IPAM requirements
Terraform scopes
Ansible scopes
verification plan
activation hold
```

without provider-native IDs in the input request.

---

# 79. Apply path

After planning is stable:

```bash
hosting apply examples/requests/internal-production.yaml --approved-plan <digest>
```

or equivalent.

Use existing authority mechanisms.

Do not invent approval by adding a boolean to a file.

---

# 80. Status path

Target:

```bash
hosting status research-prod
```

showing:

```text
generation
desired-state digest
placement
delivery state
native observation state
conformance state
activation state
containment state
```

No need for live implementation immediately if authoritative storage is external, but design the domain model correctly.

---

# 81. Verify path

Target:

```bash
hosting verify research-prod
```

to collect/consume the required current evidence and produce conformance.

A local fixture PASS must never masquerade as native production PASS.

---

# 82. Evidence path

Target:

```bash
hosting evidence research-prod
```

to assemble references to:

```text
request
profiles
placement
plan
execution
native observation
conformance
authority
```

without exposing protected raw secrets.

---

# 83. Performance and scale

Avoid designs requiring:

```text
scan every tenant state file for every request
load entire platform inventory repeatedly without caching
global lock for all provisioning
```

Design clear indexes/interfaces.

Do not prematurely optimize, but avoid obviously non-scalable architecture.

---

# 84. Extensibility

Future platforms should implement adapter contracts rather than modify portable request semantics unnecessarily.

New platform support should roughly require:

```text
capability profile
inventory provider
placement eligibility
platform adapter
Terraform/native realization
contract tests
qualification evidence
```

not a new consumer API.

---

# 85. Observability of the provisioning system

Track stage transitions.

Useful stages:

```text
REQUESTED
VALIDATED
RESOLVED
PLACED
RESERVED
PLANNED
APPROVED
EXECUTING
EXECUTED_REQUIRES_ACCEPTANCE
VERIFIED
ACTIVE
HELD
CONTAINED
RETIRING
RETIRED
```

Use existing lifecycle concepts where already defined.

---

# 86. No false production-readiness claims

Repository completion and production authorization are different.

Always distinguish:

```text
code implemented
tests passing
native qualified
site commissioned
authorized for production
```

Do not merge these states.

---

# 87. External blockers

External blockers may include:

```text
actual site inventory
installed product/API tuple
credentials
approved IP allocations
formal authority
native qualification
production change windows
```

When blocked:

```text
complete all repository-side code
complete schemas
complete validation
complete tests
complete docs
create explicit external handoff
continue elsewhere
```

Do not stop the overall refactor.

---

# 88. Completion criteria for the refactor

The refactor is not complete until all of the following are true.

## Structure

```text
[ ] current repository structure reflects current architecture
[ ] duplicate active implementation paths are removed
[ ] legacy compatibility is either justified or removed
[ ] ownership boundaries are clear
```

## Portable provisioning

```text
[ ] canonical WSD request exists
[ ] profile resolution exists
[ ] semantic policy exists
[ ] platform:auto placement exists
[ ] site/cell placement exists
[ ] internal environment compilation exists
[ ] existing WSD compiler path is integrated
[ ] Nutanix adapter path exists
[ ] VMware/NSX adapter path exists
[ ] OpenStack adapter path exists
```

## Execution

```text
[ ] plan integrates with existing Terraform/delivery mechanisms
[ ] authority boundaries remain explicit
[ ] uncertain operations reconcile before retry
```

## Verification

```text
[ ] desired vs observed model exists
[ ] conformance model exists
[ ] activation remains gated
```

## Testing

```text
[ ] unit tests
[ ] schema tests
[ ] policy tests
[ ] placement tests
[ ] compiler tests
[ ] platform contract tests
[ ] Terraform tests
[ ] Ansible tests
[ ] delivery tests
[ ] documentation tests
```

## Documentation

```text
[ ] root README current
[ ] architecture current
[ ] engineering current
[ ] implementation current
[ ] NEXT_WORK truthful
[ ] obsolete current docs removed/archived
[ ] active indexes point to current paths
[ ] historical docs clearly marked
```

## Cleanup

```text
[ ] no obsolete active schema
[ ] no obsolete active CLI
[ ] no duplicate compiler
[ ] no duplicate Terraform ownership path
[ ] no dead compatibility shim
[ ] no stale examples
[ ] no stale tests preserving removed behavior
```

---

# 89. Final repository audit

Before declaring the refactor complete:

Run repository-wide searches for:

```text
TODO
FIXME
TBD
legacy
deprecated
compat
compatibility
obsolete
superseded
old
previous
temporary
migration
shim
fallback
```

For every significant hit classify:

```text
CURRENT_REQUIRED
HISTORICAL_ONLY
TEMPORARY_WITH_EXIT_PLAN
OBSOLETE_REMOVE
```

Resolve all `OBSOLETE_REMOVE`.

Review all `TEMPORARY_WITH_EXIT_PLAN`.

---

# 90. Final documentation audit

Ask:

```text
Can a new engineer identify the current provisioning path in under five minutes?

Can they identify the portable request schema?

Can they identify how placement works?

Can they identify the platform adapter boundaries?

Can they identify what Terraform owns?

Can they identify what Ansible owns?

Can they identify what remains external?

Can they distinguish implemented capability from native qualification?

Can they distinguish current docs from historical docs?
```

If not, simplify documentation further.

---

# 91. Final code-path audit

Trace the actual current path:

```text
request
→ validation
→ profiles
→ policy
→ placement
→ allocations
→ desired state
→ environment compiler
→ platform realization
→ Terraform/delivery
→ observation
→ verification
```

Ensure there is exactly one intentional active path for each responsibility.

---

# 92. Final stale-path audit

Repository-wide search for every removed:

```text
file path
class
function
CLI command
schema identifier
Terraform root
Ansible playbook
```

No active references may remain.

---

# 93. Final test audit

Tests must represent the new design.

Remove:

```text
tests for removed CLI
tests for removed schema
tests for old compiler
tests whose only purpose is preserving deleted compatibility
```

Do not keep dead architecture alive through tests.

---

# 94. Final backlog audit

`NEXT_WORK` and implementation backlogs must describe only real remaining gaps.

Do not leave items saying:

```text
implement placement
```

after placement exists.

Do not erase genuine native/organizational blockers.

---

# 95. Final commit audit

Ensure:

```text
git status clean
small coherent commit history
no secrets
no generated junk
no half-migrated path
```

---

# 96. DeepSeek execution behavior

While performing this work:

- continue without repeatedly asking for confirmation;
- use active documentation to resolve decisions;
- use ADRs to resolve architecture;
- use existing code patterns where they are sound;
- make reasonable implementation decisions;
- do not invent production values;
- do not weaken security;
- do not fabricate qualification evidence;
- do not stop because one task is complicated;
- do not replace work with another planning document.

If a task is externally blocked, implement everything possible around it and continue to the next repository-side task.

---

# 97. Progress discipline

After every few coherent commits, reassess:

```text
What part of the target path is now real?
What old path can now be deleted?
What documentation became stale?
What is the next shortest vertical slice?
```

Prioritize completion of the vertical provisioning path over unrelated expansion.

---

# 98. Highest-priority execution sequence

Unless repository evidence shows a better dependency order, execute approximately:

```text
1. repository inventory / dependency map
2. define current authoritative path
3. create provisioner/domain structure
4. canonical request schema
5. profile catalogs and resolver
6. semantic policy validation
7. inventory abstraction
8. platform capability resolver
9. deterministic platform:auto placement
10. site/cell placement
11. capacity reservation binding
12. IPAM/service resolution
13. resolved desired-state model
14. compile to existing hosting-wsd-environment contract
15. integrate existing compile_wsd
16. platform adapter boundaries
17. plan command
18. delivery integration
19. cross-platform golden tests
20. documentation consolidation
21. legacy deletion
22. final audit
```

Do not spend the first half of the refactor merely moving files.

Deliver working behavior early.

---

# 99. Required first vertical slice

The first complete vertical slice must be:

```text
portable internal production request
→ schema validation
→ profile resolution
→ semantic policy
→ platform:auto candidate evaluation
→ deterministic placement fixture
→ hosting-wsd-environment generation
→ existing compile_wsd invocation
→ platform Terraform plan inputs
```

Make it work for at least one platform first, then bring the same request contract to all three.

---

# 100. Required cross-platform milestone

The same portable request must be capable of generating valid provider-specific realization inputs for:

```text
Nutanix
VMware/NSX
OpenStack
```

when each platform is represented by compatible qualified fixture/inventory data.

The request itself must not change provider-specific fields.

---

# 101. Required cleanup milestone

After cross-platform compilation is working:

```text
delete obsolete user-facing environment/config paths
delete superseded compiler wrappers
remove stale examples
remove stale docs
remove compatibility shims no longer needed
```

Do not postpone cleanup indefinitely.

---

# 102. Required CLI milestone

Deliver:

```bash
hosting validate <request>
hosting resolve <request>
hosting plan <request>
```

before spending major effort on additional lifecycle commands.

These commands must use the same core library.

---

# 103. Required documentation milestone

By the time `hosting plan` works:

Active docs must include:

```text
Provisioning architecture
Portable WSD request contract
Profile model
Placement model
Internal desired-state model
Platform adapter contract
Terraform execution boundary
Service-owner boundary
Plan workflow
Supported service-profile matrix
```

Retire contradictory old current docs.

---

# 104. Required quality milestone

Before enabling apply through the new interface:

Require passing:

```text
schema
semantic policy
placement
compiler
cross-platform contract
Terraform validation
delivery plan generation
documentation consistency
```

Do not connect mutation until planning is deterministic and reviewed.

---

# 105. Definition of successful refactor

A successful refactor should make the repository easier to explain:

```text
Consumer declares portable WSD intent.

The provisioner resolves standards and placement.

The existing infrastructure automation realizes the decision.

Native systems are observed independently.

Conformance determines readiness.

Authorization determines activation.
```

A successful refactor also makes the repository smaller conceptually:

```text
one current request model
one current compiler path
one placement model
one platform-adapter boundary
one active documentation story
```

even if the repository contains many provider-specific implementations underneath.

---

# 106. Ultimate objective

The final repository should support the principle:

> **Declare what environment is required, not how every provider-specific component must be assembled.**

The system should be able to:

```text
accept portable parameters
validate them
resolve profiles
enforce standards
determine eligible placement
select platform/site/cell
reserve capacity
resolve IPAM/services
compile canonical desired state
translate to platform-native infrastructure
use existing Terraform/Ansible/service-owner mechanisms
observe actual native state
reconcile uncertainty
verify conformance
produce evidence
manage lifecycle
```

while preserving:

```text
secure-by-default multi-tenancy
tenant isolation
explicit security domains
explicit trust boundaries
provider/tenant ownership separation
native qualification
separate production authorization
safe failure behavior
portable WSD intent
platform-native realization
```

---

# 107. Final instruction

Begin immediately.

Do not respond by merely restating this plan.

Do not create a second planning document and stop.

Audit the current repository against this target, identify the shortest migration path that reuses existing working implementation, and start executing the refactor in small tested commits.

Every substantial change must include the required documentation and cleanup.

When a new path replaces an old path:

```text
migrate
verify
delete
```

Do not leave both.

When documentation becomes stale:

```text
update or archive it immediately
```

When work is completed:

```text
remove it from remaining-work records
```

When an external dependency blocks native execution:

```text
finish the repository-side implementation
record the explicit external boundary
continue
```

**Git is the history.  
The working tree is the current system.  
Refactor toward one coherent, portable, parameter-driven provisioning architecture.**
