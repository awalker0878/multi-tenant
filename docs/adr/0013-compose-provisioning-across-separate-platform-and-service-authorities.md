# ADR-0013 — Compose provisioning across separate platform and service authorities

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-11`<br>
**Source chapters:** [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) · [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

One hosting request consumes resources from the selected hypervisor stack and independently owned edge, address, name, protection and trust services.

## Decision recorded in the source

Compose the required native platform and shared-service work packages. Scope credentials and Terraform state by authority, lifecycle and blast radius instead of one all-tenant, all-provider state.

## Alternatives and limits recorded in the source

The source rejects assuming one provider or a giant conditional module covers every dependency. It does not prescribe a fixed number of state files or a new orchestration application.

## Consequences

Cross-state operations are not atomic. A shared edge can require serialized ownership even while tenant workload changes proceed independently. Downstream teams need bounded handoffs, not broad state or credential access.

## Engineering and implementation obligations

Define every package's prerequisites, owned objects, accepted outputs, completion evidence and data-safe recovery action. Pin providers separately from immutable module and execution-image references.

## Requirement and code traceability

[TF-001](../assurance/requirements.md#TF-001) · [TF-002](../assurance/requirements.md#TF-002) · [TF-003](../assurance/requirements.md#TF-003) · [TF-005](../assurance/requirements.md#TF-005) · [STATE-001](../assurance/requirements.md#STATE-001) · [STATE-003](../assurance/requirements.md#STATE-003)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/roots](../../terraform/roots)
- [terraform/modules](../../terraform/modules)
- [tools/dns_change.py](../../tools/dns_change.py)
- [ansible](../../ansible)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

The actual execution platform, state backends and shared-service acceptance records remain engineering inputs.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
