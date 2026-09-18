# 3. Nutanix: realize a tenant and its workload domains

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Platform_Engineering_and_Build_Specifications.docx) · [Chapter index](README.md)

> **Source:** PBS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8c2dd9e86b4ea021922777a963534c6b52d85dff8ee398c3a12cc81287356643 -->
<a id="PBS_03"></a>

The domain routing, tenant entitlement and mandatory security selectors are different controls even when they are operated through related management services.

Design basis and related records: [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [WD §8](../../solutions/internal-protected-workload/8-mapping-the-schedules-into-each-vendor-stack.md#WD14_S08)  •  [PROV §4](../../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md#PROV_s_004)


<a id="source-table-42"></a>

| Dependency order | Native realization to specify | Owning receipt |
| --- | --- | --- |
| 1. Scope and reservation | Entitled project/RBAC scope, eligible pool, actual IPAM allocation and available attachment slot. | P4 identity, capacity and address references; no public default. |
| 2. Denied domain networks | Separate qualified VPC/routing context for each independent domain and its overlay subnets. | Native IDs, domain membership and effective baseline before endpoint access. |
| 3. Edge and forwarding | Supported external handoff with matching EC routes, policy and reply path. | P3/P4 handoff acceptance; selected NAT/no-NAT behaviour and source identity. |
| 4. Compute and data | Approved image, eligible host policy, VM/disks and only assigned networks. | P5 resource IDs, storage/key authority, required initialization and protection. |
| 5. Verify and activate | Native realization observed, service bindings verified, required readiness and authority current. | Actual observations and reversible activation; no success inferred solely from API acceptance. |

A common connected external subnet is not accepted simply because two VPCs are distinct. Native internal routing must not join OZ and RZ around the declared ZIP. No-NAT is an option only where the selected combination preserves the architecture; translation changes source attribution and return-path analysis and must be stated explicitly.

## Update and removal

Before resize, image/customization change or network reassignment, review whether the selected resource operation updates in place, requires interruption or replaces the VM. A lost response triggers task/resource discovery under the original owner. Never interpret “unknown” as permission to create another copy or delete potentially written data.

Retire only exclusively owned eligible resources. Withdraw obsolete routes and policy, reconcile outstanding tasks and address/DNS reuse, and preserve shared domains and retained copies. The actual protection and data owners decide when copy/key disposal is permissible.

Continue with: [NBD §2](../network-boundaries/2-walk-f14-01-through-the-forward-and-reply-routes.md#NBD_02)  •  [OPS §3](../../operations/recovery-transition/3-run-maintenance-and-recover-interrupted-changes.md#OPS_03)  •  [OPS §7](../../operations/recovery-transition/7-retire-live-service-separately-from-retained-data.md#OPS_07)

[Previous chapter](2-nutanix-commission-the-hosting-cell.md) · [Chapter index](README.md) · [Next chapter](4-vmware-nsx-commission-transport-compute-and-edge-roles.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0024 — Use independent Nutanix VPC domain realizations with qualified handoffs](../../adr/0024-use-independent-nutanix-vpc-domain-realizations-with-qualified-handoffs.md)

<!-- END GENERATED DECISION LINKS -->
