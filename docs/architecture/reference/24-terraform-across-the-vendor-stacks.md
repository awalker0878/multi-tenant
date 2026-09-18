# 24. Terraform across the vendor stacks

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:334 BEGIN -->

<a id="__RefHeading___Toc3686_865363315"></a>
<a id="RA_s_024"></a>

<!-- SOURCE-BLOCK RA:334 END -->

<!-- SOURCE-BLOCK RA:335 BEGIN -->

## Terraform’s architectural responsibility

<!-- SOURCE-BLOCK RA:335 END -->

<!-- SOURCE-BLOCK RA:336 BEGIN -->

Terraform provisions and maintains supported infrastructure resources through their management providers. It does not decide what the enterprise security architecture should be, independently authorize a zone transition, install every physical platform or make a workload portable by converting its data. Its inputs are approved architecture parameters and references to commissioned infrastructure. Its outputs are native resource identities, realized configuration and evidence for the responsible work package.

<!-- SOURCE-BLOCK RA:336 END -->

<!-- SOURCE-BLOCK RA:337 BEGIN -->

A deployment is composed from the chosen hosting-stack implementation and the shared services it uses. The workflow selects Nutanix, VMware/NSX or OpenStack resource modules for a domain realization, and also selects the applicable edge, IPAM/DNS, storage/protection and trust-service integrations. Selecting one vendor adapter does not remove the need to provision across those other stacks. The reference deliberately rejects a single all-platform, all-tenant state with unrestricted credentials.

<!-- SOURCE-BLOCK RA:337 END -->

<!-- SOURCE-BLOCK RA:338 BEGIN -->


<a id="source-table-338"></a>

| Execution scope | Terraform or associated execution | Inputs and outputs at the boundary |
| --- | --- | --- |
| Physical foundation | Qualified network/hardware provider where available; otherwise supported managed configuration tooling | Accepted physical design → transport and attachment capacity; separate foundation credentials |
| Nutanix resources | Qualified Nutanix provider/API modules | Eligible cluster/VPC/service parameters → owned VM, network, policy and data references |
| VMware resources | Qualified vSphere and NSX providers, separately scoped as needed | Eligible compute/storage and gateway topology → VM, segment, routing and policy references |
| OpenStack resources | Qualified OpenStack provider/API modules | Project, service/backend eligibility and quotas → instance, volume, port, router and policy references |
| Security edge | Selected supported firewall/security-service integration | Approved domain pair and flows → isolated context/policy, routes and enforcement evidence |
| Names, addresses and common services | IPAM/DNS, backup, key/identity and other supported integrations | Approved allocations/bindings → authoritative reservations, registrations and service acceptance |

<!-- SOURCE-BLOCK RA:338 END -->

<!-- SOURCE-BLOCK RA:339 BEGIN -->

<!-- SOURCE-BLOCK RA:339 END -->

<!-- SOURCE-BLOCK RA:340 BEGIN -->

The implementation records coverage per operation, not merely per provider name: create, observe, update, import/adopt, replace, delete and reconcile failure. An operation unsupported by the provider needs a documented alternative under the same lifecycle and evidence requirements. It must not be represented as completed solely by a placeholder, a no-op module or a script that cannot observe and safely update what it creates.

<!-- SOURCE-BLOCK RA:340 END -->

<!-- SOURCE-BLOCK RA:341 BEGIN -->

## Module and state boundaries

<!-- SOURCE-BLOCK RA:341 END -->

<!-- SOURCE-BLOCK RA:342 BEGIN -->

Root configurations hold provider configuration and pass the required provider references to focused modules, consistent with HashiCorp guidance. Modules express infrastructure work packages such as a domain network, workload resource set or security-edge context. They are not required to mirror every abstract object in the previous schema package. The workflow assembles them according to ownership, lifecycle and dependencies. \[[S13](34-appendix-d-sources-and-review-status.md#RA_src_S13)\]

<!-- SOURCE-BLOCK RA:342 END -->

<!-- SOURCE-BLOCK RA:343 BEGIN -->

State boundaries follow authority and blast radius: foundation, management, platform/shared services, edge, domain and workload are separately governed scopes, subdivided where necessary. The exact number of state files is an implementation decision. A shared edge may need centralized ownership and serialized updates even while per-tenant workload states run concurrently. Two states or tools must not compete to manage the same native object.

<!-- SOURCE-BLOCK RA:343 END -->

<!-- SOURCE-BLOCK RA:344 BEGIN -->

Exchange minimal versioned handoffs rather than granting broad access to another team’s state. A domain workflow can consume an attachment reference or readiness receipt without holding firewall administrator credentials. Protect state and plans with encryption, scoped authentication, locking, versioned recovery and audit. Restoring an old state file is not rollback of the real infrastructure; reconcile real resources before any further apply.

<!-- SOURCE-BLOCK RA:344 END -->

<!-- SOURCE-BLOCK RA:345 BEGIN -->

## Change execution and reproducibility

<!-- SOURCE-BLOCK RA:345 END -->

<!-- SOURCE-BLOCK RA:346 BEGIN -->

Pin supported providers and verify their packages. Commit dependency lock files, but also pin remote module references and execution images independently: Terraform’s provider lock file does not lock remote module selections. An approved change identifies its inputs, dependencies, relevant state versions and policy baseline. Stale or altered changes require re-evaluation rather than reuse of an unrelated approval. \[[S14](34-appendix-d-sources-and-review-status.md#RA_src_S14)\]

<!-- SOURCE-BLOCK RA:346 END -->

<!-- SOURCE-BLOCK RA:347 BEGIN -->

Use a gated multi-package sequence: reserve, create under deny, configure boundaries, verify, activate and record. Each package has a defined completion signal and data-safe compensation. A failed downstream step may release an unused address but must not destroy shared domains, held backups or newly written production data. Bounded retries and human recovery for ambiguous outcomes are operational requirements, not a demand for a particular saga engine or database implementation.

<!-- SOURCE-BLOCK RA:347 END -->

<!-- SOURCE-BLOCK RA:348 BEGIN -->

This document defines what the Terraform solution must provision and its execution boundaries. Working modules, provider bindings, resource arguments, schema validation and CI implementation are separate engineering deliverables. No executable cross-vendor deployment or live integration test is claimed by issuing this architecture revision.

<!-- SOURCE-BLOCK RA:348 END -->

<!-- SOURCE-BLOCK RA:349 BEGIN -->

Operation coverage is recorded per actual native resource and management tuple: observe, create, update, adopt/import, replace, delete and recover an uncertain outcome. Unsupported or externally owned operations have a named alternative and accepted handoff. PROV §3 supplies this matrix without claiming that a provider name proves full lifecycle support. PROV §5 addresses delayed native tasks and competing writers after execution failure.

<!-- SOURCE-BLOCK RA:349 END -->

<!-- SOURCE-BLOCK RA:350 BEGIN -->

Related engineering: [PROV §3 — Terraform, native tools and operation-level support](../../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md#PROV_s_003)  •  [PROV §5 — Concurrency, ownership and failed execution](../../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md#PROV_s_005)

<!-- SOURCE-BLOCK RA:350 END -->

<!-- SOURCE-BLOCK RA:351 BEGIN -->

PART 5  /  Operations and lifecycle

<!-- SOURCE-BLOCK RA:351 END -->

[Previous chapter](23-tenant-domain-and-workload-provisioning-sequence.md) · [Chapter index](README.md) · [Next chapter](25-change-brownfield-adoption-and-configuration-ownership.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0013 — Compose provisioning across separate platform and service authorities](../../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md)
- [ADR-0016 — Assign one authoritative writer per native object and sensitive subresource](../../adr/0016-assign-one-authoritative-writer-per-native-object-and-sensitive-subresource.md)
- [ADR-0031 — Discover uncertain native outcomes instead of blind replay or rollback](../../adr/0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md)
- [ADR-0038 — Govern image and privileged dependency provenance across their lifecycle](../../adr/0038-govern-image-and-privileged-dependency-provenance-across-their-lifecycle.md)

<!-- END GENERATED DECISION LINKS -->
