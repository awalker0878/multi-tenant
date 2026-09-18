# ADR-0013 — Compose provisioning across separate platform and service authorities

**Status:** Proposed<br>
**Accountable role:** Automation platform<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-11`<br>
**Source chapters:** [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) · [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.
> **Editorial extension:** this record includes a separately identified audit-remediation proposal grounded in its linked sources; no original approval is inferred.


## Context

One hosting request consumes resources from the selected hypervisor stack and independently owned edge, address, name, protection and trust services.

## Decision

Compose the required native platform and shared-service work packages. Scope credentials and Terraform state by authority, lifecycle and blast radius instead of one all-tenant, all-provider state.

## Alternatives and source limitations

The source rejects assuming one provider or a giant conditional module covers every dependency. It does not prescribe a fixed number of state files or a new orchestration application.

## Consequences

Cross-state operations are not atomic. A shared edge can require serialized ownership even while tenant workload changes proceed independently. Downstream teams need bounded handoffs, not broad state or credential access.

State services and cross-owner handoffs remain separate resource/authority scopes. Their design must identify protected backend access, recoverable state, locking/versioning and minimal versioned outputs; state restoration is not infrastructure rollback.

## Engineering and implementation obligations

Define every package's prerequisites, owned objects, accepted outputs, completion evidence and data-safe recovery action. Pin providers separately from immutable module and execution-image references. Validate these dependencies and record their owner, accepted configuration and failure/recovery observations before the affected service is offered.

## Requirement and code traceability

[TF-001](../assurance/requirements.md#TF-001) · [TF-002](../assurance/requirements.md#TF-002) · [TF-003](../assurance/requirements.md#TF-003) · [TF-005](../assurance/requirements.md#TF-005) · [STATE-001](../assurance/requirements.md#STATE-001) · [STATE-003](../assurance/requirements.md#STATE-003) · [STATE-002](../assurance/requirements.md#STATE-002)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/roots](../../terraform/roots)
- [terraform/modules](../../terraform/modules)
- [tools/dns_change.py](../../tools/dns_change.py)
- [ansible](../../ansible)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

The actual execution platform, state backends and shared-service acceptance records remain engineering inputs.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
