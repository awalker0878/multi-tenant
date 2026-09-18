# ADR-0026 — Choose and own the actual OpenStack backend and domain boundaries

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) · [VND §5](../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md) · [PBS §6](../engineering/platform-build/6-openstack-commission-a-distribution-not-a-generic-label.md) · [PBS §7](../engineering/platform-build/7-openstack-protect-mandatory-network-mutation.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [terraform/modules/openstack-route](../../terraform/modules/openstack-route)
- [terraform/modules/openstack-workload](../../terraform/modules/openstack-workload)
- [tools/neutron_observe.py](../../tools/neutron_observe.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Actual distribution policy, gateway/OVN failure behaviour, storage/key integrations and supported native lifecycle remain target qualification work.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
