# Remaining implementation after Increment04

The following remain separate from this release's local execution evidence:

| Priority / ownership | Required next work | Hold point |
|---|---|---|
| Toolchain owner | Maintain the verified Terraform/provider toolchain and committed locks now exercised by hosted CI; rerun backend-disabled module/root, schema and plan-only mock validation on every release and review any provider change before use. | Before native apply |
| Platform and security owner | Select installed releases and EC/SE firewall/context/attachment design, licensing and permitted target scope. | Before native connection or provisioning |
| Platform observers | Populate the native reconciliation gate with the exact installed API/profile, omission/default behavior, native RBAC, version-token semantics and complete accepted task/entity coverage; add supported VM/Flow/route or composite-task profiles only where the chosen service scope requires them. | Before relying on native readback |
| Recovery owner | Establish real scoped native writer fencing and current containment/quarantine evidence, then record the same-generation source-of-truth/data-impact/shared-dependency reconciliation decision. Any approved forward repair, compensation or import remains a separate mutation plan. | Before resuming interrupted mutations |
| Security/network owner | Select the actual EC/SE or distributed/shared ZIP realization and populate the security-edge assurance gate with pairwise authority, deny-first policy, native route/bypass, inspection/logging, management separation, HA/failure, capacity and current path evidence. | Before approved connectivity |
| Shared-service owners | Authoritative IPAM, DNS product/update ACL/propagation, identity/PKI/KMS/storage/backup and isolated native restore. | Before offered service promises |
| IPv6 engineering | Populate the native address-family assurance gate for the exact platform/service mode with routing/same-host enforcement, neighbor/local-protocol controls, IPv4/IPv6 security equivalence, shared-service dependencies, native MTU/PTB/fragment behavior, failure recovery, no hidden IPv4 fallback and operating acceptance. | Before native dual-stack/IPv6 offer |
| Operations/authority | Actual initial readiness, ownership, service objectives and authorized reversible activation. | Before production |

These are not closed because there are more files or passing synthetic fixtures.
[Current backlog](../sources/implementation_backlog.csv) identifies each remaining
evidence dependency and the part delivered in this increment.
