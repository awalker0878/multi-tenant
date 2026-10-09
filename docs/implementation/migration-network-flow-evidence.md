# Application-required flows and native destination security evidence

**State:** Discovery and owner-review implementation in draft PR #64. A separate
service-only E4 admission *interface* is wired to current Catalogue and Assurance;
there is no commissioned live end-to-end E4 evidence producer or migration
execution approval in these code changes. NSX enrollment and read-only
discovery exist; NSX/AHV effective security equivalence remains unqualified.

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
3. **Owner selection:** `app.planning_application_flow_reviews` stores
   existing destination `rule_native_ref` and `route_native_ref` choices,
   migration assessment ID, current published source revision, stable
   destination identity, reviewed-by actor, native semantic fingerprints and
   optimistic revision. It does **not** store a durable affirmative network
   proof. Routine observation timestamp refreshes retain reviewed selections;
   changes to the selected native control semantics clear preselected IDs and
   require fresh owner review. There is no native create-rule action.
4. **Independent destination acceptance:** Planning now rejects selections that
   do not identify exactly one matching observed firewall entry and route,
   whose scope/direction/context and allow semantics match the approved flow.
   A second independent check tests current route reachability, ingress and
   egress, return path, native receipts and measured allowed/forbidden traffic.
   Missing source coverage, stale evidence, wrong network context, mismatched
   policy/topology, fabricated IDs and observation by the writer hold admission.
5. **Execution:** The `MigrationSupport.require` gate invokes
   `MigrationFlows.require` before native route admission. It cannot accept
   saved `eligible` status alone. A service principal rereads the current
   published Catalogue revision and calls Assurance's
   `/migration-qualifications` for a signed/current E4
   `migration.application_flow_records` capability. The receipt must match
   the exact assessment, current intent, reviewed choice set, native control
   fingerprints, destination generation and a <=30-second old allow, deny,
   return-path, tenant-isolation, native-rule and application check. Missing,
   stale or unsigned evidence blocks admission; execution/cutover must repeat
   revalidation rather than treating the first check as a permanent grant.
   Optional omissions require a reason code, a separate approved receipt and
   an approver distinct from the submitting owner.

## Platform-specific current scope

| Destination | Native catalogue status | Safe Console behavior |
| --- | --- | --- |
| OpenStack | Project-scoped Neutron security group/rule IDs and literal rule fingerprints are API discovered. | Source-observed ACLs can map only to matching existing Neutron native IDs. These are **ACL mappings**, not an owner-approved application-flow dependency inventory. |
| AHV | Prism v4 Microseg discovery now reads documented `GET /api/microseg/v4.3/config/policies/{policyExtId}/rules` per scoped policy, bounded to eight policies and one page per policy. Missing or conflicting inline/native rule bodies hold discovery; only rule IDs, digests and reference IDs are projected. Categories can be observed as catalogue identities, **not** effective-policy qualification. Address/service/entity groups, IPv4/IPv6 behavior and policy order still need version-specific resolution. | Unqualified policy mappings are suppressed in the Console and rejected by Inventory; an empty draft is retained with a hold. |
| VMware | vCenter inventory alone is not NSX evidence. A separate, read-only `nsx_security.collect_nsx_policy_rules` adapter uses an explicitly commissioned, independent `target_profile.nsx_policy` HTTPS origin, pinned addresses, mounted BasicAuth credential and domain. Collection is bounded and emits only IDs and fingerprints. Service/group references and VM-to-DFW effective membership remain unqualified. | No NSX DFW security-policy dropdown or equivalence assertion is allowed from vCenter network inventory. |

## Required integration to complete the boundary

- Planning now exposes `migration-flow-choices` and `migration-flow-selections` through authenticated site-scoped, application/environment delegated APIs. The Console `MigrationSupport` screen renders native firewall and route selections for *source-approved* communication dependencies. `app.planning_application_flow_reviews` persists revisioned choices, context digests and expiry, and a runtime flow gate blocks absent/stale/held selections. This implementation still needs integration validation against a live Catalogue/Inventory/Assurance deployment and a current E3/E4 qualified native evidence producer. No runbook should label these selections a successful migration.
- The vCenter target profile can now enroll a separate `nsx_policy` object with a pinned HTTPS origin, pinned addresses, mounted credential and commissioned domain. The worker performs bounded read-only calls. **Remaining qualification:** prove the VM's actual NSX group membership, effective DFW policy ordering, resolved service and group objects, default-action semantics and version-to-API feature support.
- AHV's per-policy rule GET is wired and budgeted. **Remaining:** resolve
  all referenced native category/entity/address/service definitions using the
  exact installed Microseg release, effective network policy ordering, IPv6
  behavior, reference membership and measured service outcomes. A rule-list
  fingerprint alone never lifts the hold.
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


## Service commissioning and release gates

- Apply `services/planning/migrations/004_application_flow_reviews.sql` to the
  disposable Planning database under its owner role before the new Console
  selection workflow is exercised. Reviews are keyed by application,
  environment, site and migration assessment; the submitting actor is
  recorded separately.
- Commission authenticated, read-only Catalogue's
  `/internal/tenants/{tenant}/applications/{application}/environments/{environment}/current-planning-intent`
  and the existing Assurance `/migration-qualifications` service endpoint.
  The latter exposes `flow_evidence: null` unless the current signed E4
  runtime resolver authorizes the exact `migration.application_flow_records`
  binding. An unsigned file/registry entry is not enough.
- An E4 record binds `assessment_id`, `source_revision_id`,
  `source_intent_sha256`, `context_sha256`, `selections_sha256`,
  `native_controls_sha256`, `destination_generation_id`, platform,
  `observed_at`, `expires_at`, seven independent pass checks, and
  `omissions_sha256`. Optional omissions require `omissions_approved=true`
  and an independent `omission_approver_id` distinct from `reviewed_by_actor`.
- **No live E4 probe producer, native behavior qualification or successful
  cutover is established by the presence of these contracts.** An
  administrator must independently commission and exercise the producer and
  receiving acceptance tests before any native migration. NSX/AHV firewall
  mapping remains suppressed until their respective E3/E4 native semantics
  are qualified.
- Recheck approval at the *actual cutover* using fresh evidence, not just at
  earlier plan creation. Preserve reviewer and independent approver audit
  records. Before releasing the branch, run unit, API contract, database,
  frontend and policy-effect regression tests against current vendor API
  fixtures and real pinned TLS installations.
