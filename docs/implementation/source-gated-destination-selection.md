# Source-gated destination selection and API-owned choices

**Implementation:** Inventory worker native observations, Inventory domain
`destination_security.py`, `vmware.py`, `ahv.py`, `migration.py`,
`WorkloadProfiles.review`, and Console `Migration.vue` /
`AhvDestination.vue` / `VmwareDestination.vue`.

## Required behavior

1. **First determine whether the feature exists in the selected source
   observation.** Absence and unknown are different. A defined source NIC
   creates a required NIC-to-network mapping; no source categories means
   the AHV category selector is not rendered. Source guest OS/firmware
   must be known before compatible destination values can be offered.
   Unknown source policy rules do not become an empty rule list.
2. **Retrieve destination values only through the enrolled destination
   API and scope.** Never let the browser create a custom destination ID.
   AHV microseg policies, categories, VPCs, storage containers and
   subnets are native Prism inventory; VMware folders, pools, hosts,
   datastores and networks are native vCenter inventory. VMware guest
   IDs and hardware versions are queried per observed ESXi host from the
   VI/JSON EnvironmentBrowser QueryConfigOption API. OpenStack target
   security groups are project-scoped Neutron GET /security-groups
   objects with observed rules.
3. **Select, don't define.** The Console displays dropdowns with API-owned
   display labels and binds immutable native IDs. The server recomputes
   membership against the selected target profile, refuses forged IDs,
   requires exact source group coverage and checks that the selected
   source/target review is unchanged and current. Empty destination API
   results produce **no choice**, not a free-text fallback.
4. **Required network flows are functional and security constraints.**
   OpenStack source port security groups are enumerated through native
   Neutron port observations; the collector reads each named group
   through the scoped Neutron API. For OpenStack-to-OpenStack mappings,
   only groups with equal independently observed canonical
   direction/ethertype/protocol/port/CIDR/statefulness fingerprints
   appear as choices. Rule/group IDs and labels alone are not
   semantic equivalence. Remote security-group/address-group
   references, unknown statefulness, unknown source network state,
   mismatching rules or missing API permissions are unqualified and
   cannot be accepted as equivalent.
5. **Cross-hypervisor policies require a real adapter and receiving
   proof.** Nutanix Prism microseg policy state ENFORCE indicates an
   API-visible enforced policy *exists*, but does not prove its
   allow/deny semantics are equivalent to source Neutron rules. A
   source-to-AHV mapping may be saved as a review draft but is held
   from confirmation pending native E3/E4 policy mapping evidence.
   VMware destination currently has only network membership, not
   native NSX/ACL policy rules. A source with required security groups
   is held for target VMware until a commissioned native policy
   catalogue and independent rule equivalence check are added.
6. **Operator responsibility:** select the intended existing target
   resources; supply application datasets, dependencies, impact,
   outage/data-loss objectives and independent verification
   *references*. Operators never type destination security-group IDs,
   rule bodies, guest IDs or VM hardware versions, or overwrite
   native API facts. Independently measured allow and deny traffic,
   required application reachability, rollback and security outcomes
   remain Assurance/receiving obligations. An owner reference is not
   native evidence.
7. **No implicit firmware:** when the source cannot establish EFI/BIOS,
   the destination form does not guess BIOS. The plan is held.

## Current source-readiness gaps (fail closed)

| Source | Available source network-security evidence | Consequence |
| --- | --- | --- |
| OpenStack | Port `security_groups`, `port_security_enabled`, per-group Neutron rule response, source and destination rule semantics | Can offer exact native OpenStack rule-group matches; group references or unknown policy state still block |
| Nutanix AHV | VM NICs and category/segment references, but no complete **VM-effective microseg/security-flow** observation | Destination policy dropdown is unavailable until a trustworthy VM-effective source policy catalogue is commissioned |
| VMware | VM NIC backing, but no complete **NSX/firewall/ACL flow** inventory in the legacy source profile | Destination policy equivalence is held; vCenter network membership alone does not prove firewall semantics |

**Important:** A policy-rule match does not prove packet delivery,
reachability, segmentation or correctness of application dependencies.
Traffic-path allow *and* deny probes and receiving approval remain
mandatory, especially across dissimilar networking stacks.

## Native APIs and trust

- OpenStack: [Neutron Networking API](https://docs.openstack.org/api-ref/network/v2/):
  security groups, rules and project-scoped port membership. Source and
  target lists are bound to commissioned connection origins and exact
  target scope. Pagination/response completeness failures block.
- VMware: [EnvironmentBrowser QueryConfigOption](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/EnvironmentBrowser/moId/QueryConfigOption/post/)
  and [HostSystem.parent](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/HostSystem/moId/parent/get/).
  Query the selected host's supported guest IDs and virtual hardware,
  not arbitrary operator-entered identifiers.
- AHV: Prism v4 networking, VPC, category, subnet and microseg resource
  reads are sourced from the enrolled native API and filtered for
  project/cluster sharing and enforced policy state.

## Validation and next work

Unit tests: `services/inventory/tests/test_destination_security.py`,
`test_destination_api_options.py`, and
`workers/inventory/tests/test_openstack_security.py`,
`test_vmware_target.py`, `test_profile_collection.py`.
These cover missing source policies, duplicate/unobserved target IDs,
mismatched network rule semantics, unavailable VMware host choices and
invented destination IDs. Browser tests and CI still require hosted execution.

Remaining E3/E4 work: commissioned VMware source and target NSX/network
security APIs; Nutanix AHV VM-effective source microseg groups and
policy semantics; independent cross-platform allow/deny flow translation;
destination-native interface/API capability version qualification;
revocation-sensitive rechecks immediately before effect; and successful
end-to-end test runs. These gaps are *not* resolved by having a dropdown.
