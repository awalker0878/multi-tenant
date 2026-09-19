# Remaining implementation after Increment04

The following remain separate from this release's local execution evidence:

| Priority / ownership | Required next work | Hold point |
|---|---|---|
| Toolchain owner | Maintain the verified Terraform/provider toolchain and committed locks now exercised by hosted CI; rerun backend-disabled module/root, schema and plan-only mock validation on every release and review any provider change before use. | Before native apply |
| Platform and security owner | Populate the target-selection gate with the actual site/cell, installed tuple, EC/SE and management/OOB realization, permitted disposable campaign scope, data restrictions, credential custody, stop authority and time-bounded target-contact authority. | Before native connection or provisioning |
| Platform observers | Populate the native reconciliation gate with the exact installed API/profile, omission/default behavior, native RBAC, version-token semantics and complete accepted task/entity coverage; add supported VM/Flow/route or composite-task profiles only where the chosen service scope requires them. | Before relying on native readback |
| Recovery owner | Establish real scoped native writer fencing and current containment/quarantine evidence, then record the same-generation source-of-truth/data-impact/shared-dependency reconciliation decision. Any approved forward repair, compensation or import remains a separate mutation plan. | Before resuming interrupted mutations |
| Security/network owner | Select the actual EC/SE or distributed/shared ZIP realization and populate the security-edge assurance gate with pairwise authority, deny-first policy, native route/bypass, inspection/logging, management separation, HA/failure, capacity and current path evidence. | Before approved connectivity |
| Shared-service routing owner | Populate the origin-specific service-reply gate for every offered service binding and family with endpoint entitlement, forward/reply route ownership, alternate-path/no-transit review, source validation, missing-route/edge-failure/reverse-initiation tests, telemetry, survivor capacity and binding/version revocation evidence. | Before shared-service use |
| Shared-service owners | Populate the bootstrap service gate with current authoritative IPAM/DNS, selected address-assignment/DHCP-metadata behavior, resolver/time/trust/artifact/telemetry/service-reply dependencies, restricted management and steady-state transition evidence. Populate the identity/crypto and storage lifecycle gates separately; continue using the backup/restore gate for protection. | Before offered service promises |
| IPv6 engineering | Populate the native IPv6 assurance gate for the selected site/service/platform/security-edge mode: addressing/local protocols, route/security parity, MTU/PMTU, shared-service dependencies, failure/recovery and operational acceptance. Preserve no-IPv4-fallback evidence for IPv6-only or an independent IPv4 campaign for dual-stack. | Before native dual-stack/IPv6 offer |
| Operations/authority | Populate the production activation assurance gate with exact-scope G0/G1/G2 prerequisites, initial G4 recovery/operations readiness, current operating authority and a tested reversible G3 withdrawal plan. Execute any exposure change externally, then record live entry/reply, dependency and telemetry evidence; withdraw failed/unknown activation. | Before production |

These are not closed because there are more files or passing synthetic fixtures.
[Current backlog](../sources/implementation_backlog.csv) identifies each remaining
evidence dependency and the part delivered in this increment.
