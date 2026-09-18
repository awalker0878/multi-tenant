# 31. State Boundaries

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:258 BEGIN -->

<!-- SOURCE-BLOCK HB10:258 END -->

<!-- SOURCE-BLOCK HB10:259 BEGIN -->

Terraform state is both a blast-radius and authority boundary. State should be divided so that an automation identity can manage only the objects it is authorized to change and a failed or locked run does not block unrelated domains.

<!-- SOURCE-BLOCK HB10:259 END -->

<!-- SOURCE-BLOCK HB10:260 BEGIN -->


<a id="source-table-260"></a>

| State Domain | Typical Contents | Identity Scope |
| --- | --- | --- |
| Physical foundation | Fabric bootstrap, physical attachments, core platform foundation | Foundation automation only |
| Management foundation | OOB/MZ infrastructure and access controls | Management automation only |
| Security edge | ZIP/security contexts and provider-side edge infrastructure | Security-edge automation only |
| Security Domain | VPC/Tier-1/router, networks, baseline policies | Tenant-domain automation |
| Workload | VMs, volumes, application-level objects | Workload automation |
| Shared service | Service endpoint realization | Service-owner automation |

<!-- SOURCE-BLOCK HB10:260 END -->

<!-- SOURCE-BLOCK HB10:261 BEGIN -->


<a id="source-table-261"></a>

| STATE-001 | No single routine tenant automation identity SHALL have authority to modify physical fabric, management foundation, security edge, and tenant workloads simultaneously. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:261 END -->

<!-- SOURCE-BLOCK HB10:262 BEGIN -->


<a id="source-table-262"></a>

| STATE-002 | Remote state backends SHALL use encryption, strong authentication, locking, recovery/versioning, access logging, and separation appropriate to the sensitivity of contained data. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:262 END -->

[Previous chapter](30-terraform-architecture.md) · [Chapter index](README.md) · [Next chapter](32-policy-as-code-and-security-admission.md)
