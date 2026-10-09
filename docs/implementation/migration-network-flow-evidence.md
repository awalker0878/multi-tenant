# Application-required flows and native destination security evidence

**State:** E2 implementation in draft PR #64. No E3/E4 equivalence, application
connectivity, policy effectiveness, NSX enrollment or native-write authority is
claimed by these code changes.

## Separation of responsibilities

1. **Application intent (source truth):** Planning's authenticated application
   intent `dependencies` collection is the canonical source of required and
   optional `communication` flows. It contains logical endpoints, protocol,
   port and requirement strength. Neutron ACLs/Prism policies/NSX firewall
   entries must **never** be interpreted as application dependencies.
2. **Destination discovery:** Inventory, qualified platform collectors and
   Assurance publish project/domain-scoped, time-bounded native *existing*
   route and policy references. The new
   `native_application_flow_choices(intent, network, policy)` enumerates only
   observed, context-compatible destination-native firewall and route IDs.
   Empty choices are a hold, not a place for manually defining a native ID.
3. **Owner selection:** The proposed `application_flow_selections` record binds
   a hash of the *approved source flow four-tuple* to existing destination
   `rule_native_ref` and `route_native_ref`, plus observation age, policy and
   topology digests and a distinct observer identity. It must be stored as an
   owner-reviewed reference bound to the source intent and destination
   observation versions. Do **not** allow user-supplied rule bodies or a
   `new rule` action from a migration review.
4. **Independent destination acceptance:** Planning now rejects selections that
   do not identify exactly one matching observed firewall entry and route,
   whose scope/direction/context and allow semantics match the approved flow.
   A second independent check tests current route reachability, ingress and
   egress, return path, native receipts and measured allowed/forbidden traffic.
   Missing source coverage, stale evidence, wrong network context, mismatched
   policy/topology, fabricated IDs and observation by the writer hold admission.
5. **Execution:** Migration confirmation remains *not* write authorization.
   Lifecycle must reuse the reviewed plan and recheck admission immediately
   before effects and cutover. An independently approved plan must not be
   silently weakened by a newly available API choice.

## Platform-specific current scope

| Destination | Native catalogue status | Safe Console behavior |
| --- | --- | --- |
| OpenStack | Project-scoped Neutron security group/rule IDs and literal rule fingerprints are API discovered. | Source-observed ACLs can map only to matching existing Neutron native IDs. These are **ACL mappings**, not an owner-approved application-flow dependency inventory. |
| AHV | Prism v4 microseg policy list now projects rule extIds, types and native rule-spec SHA-256 **when policy list responses contain complete rule bodies**. Missing bodies produce `ahv_security_rule_catalog_incomplete`. Referenced categories/address and service groups and policy order still need resolution. | Unqualified policy mappings are suppressed in the Console and rejected by Inventory; an empty draft is retained with a hold. |
| VMware | vCenter inventory alone is not NSX evidence. A separate, read-only `nsx_security.collect_nsx_policy_rules` adapter now validates an explicitly commissioned NSX domain, bounded policy/rule lists, identities, read authority and incomplete pagination. This adapter is **not yet wired to a separately enrolled NSX credential/stream**. | No NSX DFW security-policy dropdown or equivalence assertion is allowed from vCenter network inventory. |

## Required integration to complete the boundary

- Expose the approved Planning intent and current independently observed network
  snapshot together through a scoped, read-only API for the owning application
  and migration, returning `native_application_flow_choices`. The existing
  `migration-support` endpoint currently reports route qualification only.
- Render a dedicated **application-flow** mapping section in the Console: for
  each required source dependency, select existing destination firewall and
  route IDs from read-only API choices. Persist the digest-bound, typed owner
  selections in a reviewed record, never free text or a native write request.
- On save and confirmation, verify that this record's source intent hash,
  destination observation digest, tenant/site/project, expiry and ownership
  still match. On refresh/revocation, clear selections and confirmation. Deny
  incomplete mappings before execution.
- Wire a separately commissioned NSX Policy API origin and least-privilege
  credentials to the approved vCenter installation; prove the VM's actual NSX
  group membership, effective DFW policy ordering, resolved service and group
  objects and default-action semantics. Never use the vCenter credential or
  API origin to call NSX.
- Extend AHV collector to the version-qualified rule-list endpoint if the
  selected Prism release does not include rules in the policy response.
  Authorize every extra API GET, bound all paging/request budgets, resolve
  group/service references and prove effective enforcement.
- Establish E3 native allow/deny, routing, return-path and policy-effect
  witnesses for each platform and E4 independent application, tenant isolation,
  cutover and receiving approval. Only then register a cross-platform rule
  translation as qualified.

## API documentation

- OpenStack Neutron security-group rule endpoints:
  https://docs.openstack.org/neutron/latest/configuration/policy.html
- VMware NSX Policy API security policy and rule lists:
  https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ListSecurityPoliciesForDomain.html
  and
  https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ReadSecurityRule.html
- Nutanix microseg API and rule models:
  https://developers.nutanix.com/api/v1/sdk/namespaces/main/microseg/versions/v4.2/languages/python/ntnx_microseg_py_client.api.network_security_policies_api.html
  (the actual installation's microseg API version must be separately qualified).

**Note:** The new read-only choice builder and independently assessed
`application_flow_selections` are **not yet wired into the Console as a
complete workflow**. Do not claim this feature shipped end-to-end.
