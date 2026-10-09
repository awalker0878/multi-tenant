# Native security equivalence: qualification and commissioning contract

**Status:** A conservative E4 evaluator, version-bound admission interface, bounded
NSX/Prism discovery and negative-path tests are implemented on draft PR #64.
**No live E4 observer/NSX-AHV producer has yet been commissioned.**
This is a release hold, not a declaration of production equivalence.

## Trust and ownership

1. Catalogue owns the latest published application flow, including mandatory
   and optional dependencies. A native firewall rule list is **not** the source
   of application-flow requirements.
2. Inventory owns read-only, TLS-pinned, provider-version-qualified E2
   discovery. It cannot infer an effective VM security posture from existence
   of a policy or group.
3. Assurance owns independently signed runtime E4 evidence and a distinct
   observer principal. The `migration.effective_security` capability must
   bind the exact hash of `capability_snapshot.data.effective_security_cases`
   for the installed destination platform and scope. Unqualified cases never
   appear as Console destination-native dropdown options.
4. The native owner reviews existing **rule native reference** and a complete
   **path fingerprint** (`path:<sha256>`) from those qualified cases. These
   are selectors only, not authorizations to create or modify native rules.
5. At migration admission and every lifecycle stage revalidation, Planning
   reads current Catalogue intent and a fresh, signed E4
   `migration.application_flow_records` receipt from Assurance, bound to
   source and destination platform, exact profile fingerprints, migration
   method, selected native control semantics, destination generation, source
   revision, independent omission approval, and the full selected flow set.
   Missing, changed or expired evidence fails closed.

## VMware NSX provider qualification

* Enroll the NSX Policy API separately from vCenter, with its own pinned TLS
  origin, CA/trust path, permission-scoped read-only credentials and domain.
* E2 collector reads `/policy/api/v1/infra/domains/{domain}/security-policies`,
  each policy's `/rules`, `/domains/{domain}/groups` and
  `/infra/services`. Every paginated/over-budget response fails closed.
* Preserve policy **category**, **sequence_number**, **stateful**, applied-to
  **scope**, and rule **sequence_number**, action, direction and native
  source/destination group and service paths. NSX distributed L3 categories
  have fixed precedence (Emergency, Infrastructure, Environment,
  Application); Ethernet is L2 and cannot establish L3 application access.
  Duplicate effective priority, unknown category or policy state is held.
* Actual group **effective members**, nested/dynamic tag evaluation, excluded
  members, service entries/protocol/port expansion, rule effective applied-to,
  and native default action must be proven by an independent observer on the
  installed API release. E2 group expressions and service-list fingerprints
  are intentionally `unverified` even if they appear complete.
* Native `ANY` is recorded as a wildcard requiring E4 proof, not treated as
  a resolved group or proof of least privilege.

Relevant official references:
- https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/types_SecurityPolicy.html
- https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ListGroupForDomain.html
- https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ListServicesForTenant.html
- https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ListServiceEntries.html

## Nutanix AHV/Prism Microseg provider qualification

* A dedicated Prism v4.3 observer reads native policy configuration and
  `/api/microseg/v4.3/config/policies/{policyExtId}/rules` under explicit
  budgets, and separate `entity-groups`, `address-groups`, `service-groups`
  collections. All identifiers and native definitions are fingerprinted.
* Rule reference IDs, categories, address/service/entity groups, policy state,
  exceptions/secured-group attachment, v4 API feature availability,
  IPv4/IPv6 matching and effective ordering must be resolved per installed
  Prism version. Definitions alone stay marked `definition_only`.
* Independent E4 verification must establish **actual** affected VMs,
  rule order and enforcement state, exclusion semantics and positive/negative
  behavior. Rule presence, `ENFORCE` and a fingerprint are never sufficient.

Relevant official references:
- https://developers.nutanix.com/api/v1/sdk/namespaces/main/microseg/versions/v4.2/languages/python/ntnx_microseg_py_client.api.network_security_policies_api.html
- https://developers.nutanix.com/api/v1/sdk/namespaces/main/microseg/versions/v4.2/languages/python/sdk_reference.html

These public SDK examples describe v4.2. A v4.3 deployment must confirm its
**actual installed** namespace and endpoint contract before enabling each
v4.3 collector operation. An endpoint returning a structurally valid JSON
document does not establish that the installed version supports enforcement
semantics or an E4 acceptance profile.

## Normalized effective E4 packet/path certificate

`planning.domain.effective_security.qualify` is a pure fail-closed checker;
the caller must obtain its input from signed and current Assurance custody.

Each E4 source and destination document must contain:

- Independent observer and separate native configuration writer, observation
  and expiry times (maximum 30-second probe age), native topology digest and
  observed default-deny native enforcement point.
- **Group IDs -> complete, effective member identities**, explicitly marked
  `effective_native_members`, with revision fingerprints. A dynamic or nested
  expression alone cannot satisfy this.
- **Service IDs -> complete native protocol/port expansions**, revision hashes,
  and no unsupported semantics.
- Ordered native rules with total deterministic priority; native policy
  category/sequence (NSX), stateful enforcement, direction, effective
  attachment, enabled state, source/destination groups and native service refs.
  The **first matching** effective rule must be a stateful bidirectional allow.
  A higher-priority deny blocks migration.
- A deterministic actual directed route, 2..33 nodes / max 32 hops, no loops,
  native ref and measured forward/return for **each hop**. Unqualified ECMP,
  policy routing or route gaps block.
- For every SNAT/DNAT/twice-NAT hop: independently observed native translation
  ID, before/after source/destination IP, transport port transformations,
  stateful reverse translation and any authorized VRF/scope crossing. Unknown
  IPv4/IPv6 translation or a scope change without qualified NAT blocks.
- **Two distinct native receipts**: successful authorized source flow and
  separately observed denial of a forbidden source flow, at an independently
  observed enforcement point and same current topology. A deny asserted for
  the same required source flow is invalid.
- Explicit source/destination platform and installed profile binding; source
  and receiving environment must **both** be evaluated against the same
  logical approved application dependency. No same-name policy translation.

An E4 success returns the winning **existing** destination rule reference and
the fingerprint of the **complete** observed path, not a newly created control.

## Holds, test matrix and commissioning

- Unit matrix: `services/planning/tests/test_effective_security.py` covers
  VMware NSX, Nutanix AHV and OpenStack, measured multi-hop and stateful NAT,
  qualified VRF crossing, rule priorities, higher denies, missing group/service
  membership, stale observations and missing negative tests.
- Connector tests: `workers/inventory/tests/test_nsx_security.py`,
  `workers/inventory/tests/test_ahv_profile.py` assert bounded independent
  reads, origin scope, rule refs and unqualified E2 statuses.
- Admission: `services/planning/tests/test_migration_flow_admission.py`
  checks signed current E4 receipts, source revision, native semantic digests,
  expiry, independent omissions and platform/version binding.
- **Operational requirement:** commission physically separate native observers
  and source/destination test agents, capture provider-authoritative effective
  membership/rules/paths, run allow and forbidden-deny traffic tests, publish
  signed E4 qualification through Assurance, test revocation and post-cutover
  renewal, then run full database/CI/environment-specific vendor conformance.
  Until that evidence is available, the feature remains held. Do not enable
  fallback to E2 API discovery, manual ACL mapping, or operator-created rules.
