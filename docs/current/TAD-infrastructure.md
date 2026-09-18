# TAD-M01 — Technical infrastructure composition

**Version:** 0.1 · **Status:** Proposed · **Accountable role:** Platform, network and security engineering.

## Scope and authority

Technical decomposition across the fabric, hosting stacks, security edge and shared services.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §3](../architecture/reference/3-system-context-and-physical-hosting-topology.md) · [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md).

## Design content

A commissioned hosting cell provides accepted transport, eligible compute/storage, controlled management and finite attachment/security capacity. The fabric carries the supported underlay and approved physical services; it does not silently federate vendor overlays. Each independent domain instance maps to the chosen VPC, Tier-1/upstream context, Neutron/backend context or qualified physical realization.

All inter-domain transitions have named adjacent authorities and the complete required ZIP functions. Forward/reply routes, NAT/PBR interactions, source identity, policy scope and high-availability behaviour are part of that technical design. Shared EC/SE appliances may support independent logical contexts only with accepted administration, capacity and failure-sharing consequences.

Separate virtual disk I/O, guest file/object access, storage replication, backup transfer and their control planes. Shared service consumption grants only an endpoint/operation/resource scope, not provider administration. Identity, DNS, time, state, keys, backup catalogue and emergency access form a recovery dependency graph which must remain viable for the declared failure.

Native realization must name the actual product/API/provider/feature/entitlement combination. No single provider provisions or qualifies the complete environment. VMware/NSX, Nutanix and OpenStack offer different forwarding and control mechanisms; portability is a demonstrated outcome rather than topology identity.

## Engineering and implementation handoff

The LLD supplies actual native identities, interfaces, addresses, limits, support evidence, privilege scopes and code artifacts. P0–P6 assigns one resource writer per lifecycle scope. Terraform roots, supported installers, service-owner integrations and Ansible procedures consume accepted handoffs without sharing unrestricted credentials.

## Acceptance and open work

Missing native edge construction, platform commissioning, actual IAM/backup/key integrations and tested failure behaviour stay open. Record accepted operation coverage for create/observe/update/adopt/replace/delete and uncertain completion; a valid plan is not a TAD acceptance.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
