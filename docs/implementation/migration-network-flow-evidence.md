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
| AHV | Prism v4 microseg policy list now projects rule extIds, types, native rule-spec SHA-256 and explicit category/address-group/service-group reference IDs **when policy list responses contain complete rule bodies**. Only category IDs actually returned by the same observed catalogue can be provisionally resolved as catalogue identities, never policy equivalence. Missing bodies produce `ahv_security_rule_catalog_incomplete`. Referenced categories/address and service groups and policy order still need resolution. | Unqualified policy mappings are suppressed in the Console and rejected by Inventory; an empty draft is retained with a hold. |
| VMware | vCenter inventory alone is not NSX evidence. A separate, read-only `nsx_security.collect_nsx_policy_rules` adapter uses an explicitly commissioned, independent `target_profile.nsx_policy` HTTPS origin, pinned addresses, mounted BasicAuth credential and domain. Collection is bounded and emits only IDs and fingerprints. Service/group references and VM-to-DFW effective membership remain unqualified. | No NSX DFW security-policy dropdown or equivalence assertion is allowed from vCenter network inventory. |

## Required integration to complete the boundary

- Planning now exposes `migration-flow-choices` and `migration-flow-selections` through authenticated site-scoped, application/environment delegated APIs. The Console `MigrationSupport` screen renders native firewall and route selections for *source-approved* communication dependencies. `app.planning_application_flow_reviews` persists revisioned choices, context digests and expiry, and a runtime flow gate blocks absent/stale/held selections. This implementation still needs integration validation against a live Catalogue/Inventory/Assurance deployment and a current E3/E4 qualified native evidence producer. No runbook should label these selections a successful migration.
- The vCenter target profile can now enroll a separate `nsx_policy` object with a pinned HTTPS origin, pinned addresses, mounted credential and commissioned domain. The worker performs bounded read-only calls. **Remaining qualification:** prove the VM's actual NSX group membership, effective DFW policy ordering, resolved service and group objects, default-action semantics and version-to-API feature support.
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

**Note:** The application-scoped flow dropdown workflow is wired in source code but is not operationally qualified or deployed. Planning explicitly withholds NSX and AHV firewall-rule dropdowns until an E3/E4 provider-specific qualification path resolves effective policy semantics; Neutron and owner-dependency flows remain distinct. If owner inputs, live API discovery, independent native measurements, policy resolution, or current permissions are missing, the selections remain held. Do not claim NSX/AHV security policy portability or E3/E4 completion.
