# ADR-0013 — Compose provisioning across separate platform and service authorities

**Status:** Proposed<br>
**Accountable role:** Infrastructure automation and state-service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-11`<br>
**Source chapters:** [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) · [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/roots](../../terraform/roots)
- [terraform/modules](../../terraform/modules)
- [tools/dns_change.py](../../tools/dns_change.py)
- [ansible](../../ansible)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

The actual execution platform, state backends and shared-service acceptance records remain engineering inputs.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

## Proposed clarification — Protected state and minimal cross-owner handoffs

The accepted backend must demonstrate encryption, authentication, lock ownership, audit/version history and recovery under the declared failure. Export minimal non-secret immutable references between owners rather than share unrestricted state. Restoring state bytes is not native infrastructure rollback.

Source basis: [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) · [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md). This clarification is not an accepted historical decision.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
