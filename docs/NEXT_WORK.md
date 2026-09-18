# Remaining implementation after Increment04

The following remain separate from this release's local execution evidence:

| Priority / ownership | Required next work | Hold point |
|---|---|---|
| Toolchain owner | Obtain verified Terraform/plugins; initialize with backend disabled, validate modules/roots, export actual schemas/locks, execute plan-only mocks and fix any native-schema defects. | Before native apply |
| Platform and security owner | Select installed releases and EC/SE firewall/context/attachment design, licensing and permitted target scope. | Before native connection or provisioning |
| Platform observers | Qualify these exact NSX/Nutanix selected-field profiles against the real APIs, omission/default behavior, native RBAC, task metadata and expected-token capture; add supported VM/Flow/route and composite-task profiles separately. | Before relying on native readback |
| Recovery owner | Implement true scoped fencing, task tracking, state reconciliation and authorized forward repair against the selected native toolchain. Record-only triage does not supply those actions. | Before resuming interrupted mutations |
| Security/network owner | Build actual domain/service attachments, route and policy/inspection realization, HA and complete path evidence. | Before approved connectivity |
| Shared-service owners | Authoritative IPAM, DNS product/update ACL/propagation, identity/PKI/KMS/storage/backup and isolated native restore. | Before offered service promises |
| IPv6 engineering | Complete native routing/local protocols/enforcement and routed IPv6 testing; AAAA and loopback tests are insufficient. | Before native dual-stack/IPv6 offer |
| Operations/authority | Actual initial readiness, ownership, service objectives and authorized reversible activation. | Before production |

These are not closed because there are more files or passing synthetic fixtures.
[Current backlog](../sources/implementation_backlog.csv) identifies each remaining
evidence dependency and the part delivered in this increment.
