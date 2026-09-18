# ADR-0026 — Choose and own the actual OpenStack backend and domain boundaries

**Status:** Proposed<br>
**Accountable role:** Platform engineering<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) · [VND §5](../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md) · [PBS §6](../engineering/platform-build/6-openstack-commission-a-distribution-not-a-generic-label.md) · [PBS §7](../engineering/platform-build/7-openstack-protect-mandatory-network-mutation.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

OpenStack distributions and Neutron backends differ. A project, router or availability-zone label does not establish a security boundary or actual physical independence.

## Decision

Record the selected service/distribution/backend combination; ML2/OVN is the illustrated reference. Keep independent domains in distinct Neutron routing/network contexts with controlled external attachments and provider-owned mandatory policy.

## Alternatives and source limitations

Other backends and delegated services require their own realization evidence. Direct edits to OVN/OVS must not compete with Neutron ownership.

## Consequences

Internal routing can be distributed independently of external gateway handling. Default groups, allowed address pairs, floating-IP paths, scheduler constraints and Cinder attachment authority need distinct controls.

## Engineering and implementation obligations

Specify controller/database/messaging, gateway and compute placement; API policy; mandatory mutation authority; approved metadata/bootstrap access; and full port/router retirement.

## Requirement and code traceability

[OS-001](../assurance/requirements.md#OS-001) · [OS-002](../assurance/requirements.md#OS-002) · [OS-003](../assurance/requirements.md#OS-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [terraform/modules/openstack-route](../../terraform/modules/openstack-route)
- [terraform/modules/openstack-workload](../../terraform/modules/openstack-workload)
- [tools/neutron_observe.py](../../tools/neutron_observe.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual distribution policy, gateway/OVN failure behaviour, storage/key integrations and supported native lifecycle remain target qualification work.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
