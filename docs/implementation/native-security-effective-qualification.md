# Effective security qualification and source-to-destination admission

**Engineering state:** Draft PR #64 implements a provider-specific **v2**
evaluation boundary, independent read-only collection components, a
finite policy-exposure comparison, complete native packet-path verification,
and a fail-closed Planning/Assurance admission integration.

**Operational state:** No NSX, AHV or OpenStack environment is connected to a
commissioned, separately authenticated E4 native policy and active-test
campaign in this PR. No live E4 result, production acceptance or successful
cutover is claimed. CI must pass before review/merge.

## Architecture

1. **Catalogue** publishes the current application dependencies (critical,
   preferred, optional) and the active revision hash. Operator or provider
   ACLs never become application requirements automatically.
2. **Inventory** collects read-only E2 platform configurations under pinned
   origins, project/tenant scope and bounded API versions. E2 group policy IDs
   alone are *not* effective workload membership or E4 acceptance.
3. **Separate provider observers** collect effective NSX VM members and
   service entries and AHV VM/category/NIC associations. These outputs
   explicitly remain E3 observations until independently qualified and
   tested by a receiving environment.
4. **Provider-specific E4 resolvers** in
   `services/planning/src/planning/domain/policy_resolvers.py` interpret
   normalized installed-version evidence:
   - **NSX:** DFW/Gateway layer, fixed category ordering, policy versus rule
     Applied To precedence, observed VM/group and L4 service attachment.
     Incomplete DFW+Gateway chains are held; Ethernet L2 behavior is not
     converted into an L3 application decision.
   - **AHV:** installed Microseg enforcement state, application/isolation/
     quarantine policies, provider-resolved effective priority, VM category
     attachment, complete exception semantics.
   - **Neutron:** per-port additive ingress+egress allow rules, security-group
     statefulness, remote member expansion, default deny, built-in anti-spoof
     behavior, port attachments, IPv4/IPv6 semantics. It never uses the
     generic NSX/AHV first-match order.
5. **Policy boundary** in `security_boundary.py`: compare each
   independently witnessed required, forbidden and observed traffic class
   in a bounded *complete attested universe*. A receiving environment
   cannot introduce access denied by the source. Unenumerated wildcards,
   an absent required or forbidden Catalogue/policy flow, or missing
   independent source/destination receipts are mandatory holds. A small
   sample is **not** claimed to prove an exhaustive policy boundary.
6. **Packet path** in `packet_paths.py`: bounded deterministic all-path
   ECMP/PBR evidence, complete logical workload/native VM association,
   directed hop IDs and forward/reverse observations, full packet tuples
   (source/destination IP, source/destination port, protocol, address family,
   VRF/scope), explicit stateful NAT/PAT and independently approved
   scope crossings. Unknown routes, incomplete ECMP alternatives, absent
   return behavior or unqualified translation block.
7. **Assurance** issues signed, independently runtime-qualified E4 receipts,
   never derived from the Console. The receipt is tied to current Catalogue
   revision, selected source/target API profile, method, installed scope,
   destination observation, owner-reviewed native controls, entire policy
   boundary and explicitly approved omissions.
8. **Planning/Lifecycle** renew current approval at native stage admission
   and cutover. Reviewer choices persist across expiring receipt refreshes
   only while the **native security semantics** are unchanged; an updated
   native group/rule/path/port or source boundary invalidates them.

## Closed-world native policy partition

**A finite set of allowed and denied probes alone cannot establish that a
receiving platform introduces no additional effective access.** The common
E4 contract therefore requires an independently attested
`disjoint_effective_rule_partition` for **each** source and destination.

- The partition must enumerate the exact same approved traffic-class
  universe on both sides, with no uncovered classes or unbounded wildcards.
  Its independently observed permitted-class set must agree with the
  provider resolver for every member of that universe.
- The attestation binds the exact native rule set, group membership,
  service expansions, port attachments, workloads, API profile, native
  observer, policy generation, and all observed positive/negative receipts.
  Any rule or attachment change invalidates the partition.
- The full native partition expansion must be supplied by a commissioned
  and separately signed E4 provider observer. This branch implements the
  **consumer and fail-closed validation**, not a claim that such an observer
  has been installed or that finite test samples are exhaustive.
- Until an installed NSX/Prism/Neutron provider can enumerate all relevant
  effective rules (including wildcard, nested, identity and direction
  semantics) without losing any permitted traffic space, partition
  qualification remains held. No manual "complete" checkbox is acceptable
  as standalone E4 proof.

**NSX realized VM identity:** The observer reads independently qualified
effective member types and `RealizedVirtualMachine.compute_ids` (including
the native `externalId`). Groups containing IP/VIF/segment membership
cannot be declared empty merely because the VM-member endpoint returns
zero records. Group observations are pinned to an explicitly qualified
`enforcement_point_path`; unqualified enforcement domains remain held.

## Installed API version policy

The versioned data registry is
`contracts/capabilities/native-security-api-registry-v1.json`.
Supported **candidate namespaces** (not implied capability approval):

| Provider | Namespace | Candidate versions |
| --- | --- | --- |
| VMware NSX | Policy API | v1 (requires exact installed NSX release and feature receipt) |
| AHV | Microseg | v4.2, v4.3 independently from VMM, Prism and Networking |
| OpenStack | Neutron | v2.0 with installed extension and statefulness checks |

`native_security_api.py` requires the independent observer's installed
build, namespace, origin, complete required-feature list, scope, owner
profile SHA and an exact feature-evidence digest. It does not grant rights
from a version string alone. AHV Inventory now constructs independently
versioned native API paths only from approved namespace profiles; optional
Microseg group endpoint paths must be explicitly commissioned or are recorded
as holds without breaking unrelated VM/storage/network inventory.

The native API registry includes candidate endpoints, but **not** a
declaration that every release supports all semantics. Do not manufacture
undocumented versions, endpoints or object shapes.

## Observer/probe separation

- `workers/inventory/src/inventory_worker/infrastructure/nsx_effective_observer.py`:
  separate mounted observer credential and origin; read-only, bounded Policy
  Group VM members and native service entry expansion; rejects incomplete
  cursors, nested/multi-service uncertainty and oversized groups.
- `workers/inventory/src/inventory_worker/infrastructure/ahv_effective_observer.py`:
  independently scoped and version-qualified VMM VM/category/NIC
  observations. Actual Microseg exception/default-action equivalence
  **still requires separately qualified provider-native evidence**.
- `workers/inventory/src/inventory_worker/infrastructure/security_probes.py`:
  executes only already-approved scoped probe plans via injected native and
  application probe agents. An allowed probe needs an application handshake
  **and** a matching native allow trace; a denied probe needs an actual native
  deny/drop receipt and increased counter, not merely a timeout.
- These worker outputs are expressly marked `observed_not_authorized` or
  `E3_observation_only`. Independent acceptance and signatures are
  performed by the existing Assurance NativeQualification custody boundary.
  No worker has native write authority.

## Destination Console

For each source-defined application flow, only authenticated API/evidence
generated existing native references appear. An attested multihop route has
a composite `path:<sha256>` **internal selector**, with actual observed route
and NAT native IDs shown as provenance. That digest is never presented as a
provisionable native route or manually accepted input.

Missing optional flows can be submitted for a reason-coded receiving-owner
waiver. A distinct receiving approver must approve a digest of the exact
omissions in the current E4 record. Missing critical flows are not waivable.
Legacy E2 OpenStack options are displayed for **draft review only**, never
sufficient to pass E4 cutover.

## Acceptance matrix

Code-level tests:

- `services/planning/tests/test_effective_security.py`: all six
  source/destination provider combinations, additive Neutron semantics,
  policy expansion denied, NSX and AHV precedence, ECMP, NAT/PAT, wrong
  attachment, stale probe, API namespace v4.2/v4.3 qualification, semantic
  control drift and explicit optional omissions.
- `services/planning/tests/test_migration_flow_admission.py`: service-only
  current Catalogue revision, signed E4 source/target packet cases, exact
  installed profiles and method, selected native semantic hash, expiring
  receipts and separate receiving approval.
- `workers/inventory/tests/test_native_security_observers.py`: NSX VM
  members and service entries; AHV native VM categories/NIC IDs; correlated
  positive and negative native traces; timeout-only denials rejected.
- `workers/inventory/tests/test_ahv_profile.py`,
  `workers/inventory/tests/test_nsx_security.py`: read bounds, scope,
  optional installed-version endpoints and absence of E2 security claims.
- Inventory and Planning authoritative OpenAPI/schema mirrors and generated
  Console types/operation digest must agree.

**Mandatory operational sign-off before the draft can merge or admit native
workloads:**

- Commission *separate* read-only E3/E4 observers and active probe agents
  in each source/destination security domain. Configure real signed
  Assurance qualification, scoped ingestion, time sync and revocation.
- Validate every enabled provider native API operation against the exact
  installed NSX/Prism/Neutron release, including AHV category exceptions,
  realized NSX scope and Neutron implicit rules.
- Capture full source and receiving effective policy universe, independent
  allowed and forbidden source/target traffic, path, return, isolation,
  negative cross-tenant/management/IPv6 tests, and post-cutover renewal.
- Run all unit, static, schema/generation, PostgreSQL, HTTP authorization,
  Playwright and provider-live tests; resolve every required CI failure.
- Exercise rollback, expiration, evidence revocation, concurrent source
  intent changes, changed installed API features and native priority drift.
- Keep missing/incomplete evidence held. **No policy weakening, fabricated
  destination resource, or E2 fallback to E4 is permitted.**

## Implementation ledger and uncompromised release gates

| Phase | Engineering status | Release gate |
| --- | --- | --- |
| 1. Correct generic matching and forbidden-flow bypass | Implemented: native provider resolvers, source/destination complete forbidden-flow checks | P05 conformance and signed E4 |
| 2. Versioned NSX, AHV and Neutron effective policy | Implemented: provider-specific policies; versioned feature registry and consistency CI; E3 native observers | Installed NSX/AHV/Neutron feature-by-feature provider certification |
| 3. Native VM/NIC/group binding | Implemented: tenant/port/IP identities, NSX realized `compute_ids` and enforcement point; AHV categories/NICs | Independent live network attachment and effective default-rule witnesses |
| 4. ECMP, PBR, NAT/PAT and return path | Implemented: complete finite directed path set, full packet tuple transitions and native refs | Positive/negative traffic and route-revision conformance under real equipment |
| 5. Independent E4 qualification | Implemented: scoped observer interfaces, native trace/counter check, signed Assurance consumption, closed-world partition verification | **Not commissioned:** separate native trust identities, active probe infrastructure, exhaustive native partition producer and signed live receipts |
| 6. Exact source/destination permission comparison | Implemented: native-rule-bound disjoint policy partitions, no destination access expansion, required and forbidden flow coverage | Independently demonstrated full IPv4/IPv6, wildcard, implicit, inter-tenant, ingress/egress coverage |
| 7. Console and omitted optional flows | Implemented: evidence selectors with native route/NAT provenance and distinct receiving waiver approval | Browser integration/Playwright and real receiving approval |
| 8. Regression and lifecycle | Added version/priority/attachment, NAT/path, partition, drift, source freshness, omission and revocation tests; lifecycle admission re-reads E4 | All applicable workflows green, E4 refresh/expiry and actual cutover/rollback/rehearsal tests |

**No simulated success is promoted to production qualification.** A queued
workflow, schema parity, unit fixture, E2 inventory record or single packet
trace is not sufficient to satisfy the release gate. Keep draft until the
commissioned native E4 producer has demonstrated that its complete rule
partition (including unspecified address families and implicit built-in rules)
is accurate for the installed versions and exact workload scope.

## Vendor reference points

- Broadcom NSX policy category/scope documentation:
  https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_GetIdsSecurityPolicy.html
- NSX effective VM group membership:
  https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_GetGroupVMMembers.html
- NSX native service entries:
  https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ListServiceEntries.html
- Nutanix Prism v4.3 category API:
  https://developers.nutanix.com/api/v1/sdk/namespaces/main/prism/versions/v4.3/languages/python/ntnx_prism_py_client.api.categories_api.html
- Nutanix v4.3 VM category metadata:
  https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.3/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.Vm.html
- OpenStack Neutron security groups:
  https://docs.openstack.org/neutron/latest/admin/intro-os-networking.html
