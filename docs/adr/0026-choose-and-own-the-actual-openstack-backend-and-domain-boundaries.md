# ADR-0026 — Choose and own the actual OpenStack backend and domain boundaries

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) · [VND §5](../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md) · [PBS §6](../engineering/platform-build/6-openstack-commission-a-distribution-not-a-generic-label.md) · [PBS §7](../engineering/platform-build/7-openstack-protect-mandatory-network-mutation.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

OpenStack distributions and Neutron backends differ. A project, router or availability-zone label does not establish a security boundary or actual physical independence.

## Decision recorded in the source

Record the selected service/distribution/backend combination; ML2/OVN is the illustrated reference. Keep independent domains in distinct Neutron routing/network contexts with controlled external attachments and provider-owned mandatory policy.

## Alternatives and limits recorded in the source

Other backends and delegated services require their own realization evidence. Direct edits to OVN/OVS must not compete with Neutron ownership.

## Consequences

Internal routing can be distributed independently of external gateway handling. Default groups, allowed address pairs, floating-IP paths, scheduler constraints and Cinder attachment authority need distinct controls.

## Engineering and implementation obligations

Specify controller/database/messaging, gateway and compute placement; API policy; mandatory mutation authority; approved metadata/bootstrap access; and full port/router retirement.

## Requirement and code traceability

[OS-001](../assurance/requirements.md#OS-001) · [OS-002](../assurance/requirements.md#OS-002) · [OS-003](../assurance/requirements.md#OS-003)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [terraform/modules/openstack-route](../../terraform/modules/openstack-route)
- [terraform/modules/openstack-workload](../../terraform/modules/openstack-workload)
- [tools/neutron_observe.py](../../tools/neutron_observe.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Actual distribution policy, gateway/OVN failure behaviour, storage/key integrations and supported native lifecycle remain target qualification work.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
