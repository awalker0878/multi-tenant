# Acceptance and release gates

[1.0 index](README.md) · [Completion backlog](completion-backlog.md) · [Required process](delivery-process.md)

## Definition of complete

An offered environment is complete when an authorized operator can use versioned, documented inputs to commission or adopt it, provision an isolated tenant/WSD, configure its workloads, bind required services, verify and activate it, then change, recover and retire it with consistent ownership and retained evidence. Ordinary approved allocation must not depend on undocumented console clicks or manually copying IDs between scripts. Supported installer/service-owner steps may remain separately owned if their invocation, receipts and recovery are integrated.

The core 1.0 claim requires this for **Nutanix, VMware/NSX and OpenStack**, for every declared baseline lifecycle target and service profile. Partial completion on one stack is a platform milestone, not three-stack completion. Conditional profiles must be either qualified or explicitly excluded from the release offer.

## Evidence levels

| Level | Required check | Claim it supports |
| --- | --- | --- |
| Source consistency | Structure, links, ownership, pinned dependency review, secret-pattern checks, unit/negative tests | Source is internally consistent within the checks' limits |
| Actual engines | Terraform validation/plan mocks and Ansible syntax/idempotence/check mode for the code being tested | Selected engine behavior; mock providers and localhost do not prove native behavior |
| Native restricted campaign | Real installed tuple, scoped APIs, guest configuration, packets/data, failure/recovery and cleanup | Only the tested capabilities/operations under the actual observed limits |
| Accepted service offer | Current provenance, campaign/dossier, capacity, shared-service evidence, operating/recovery readiness | Eligibility for the declared service envelope, subject to its conditions |
| Production change | Current authority, exact approved change and post-activation observations | The specific service activation/change, with withdrawal on failed or unknown verification |

## Native acceptance matrix

Every row is **OPEN** for all three stacks at the audit baseline. Existing local tests can be reused, but they do not fill native evidence cells. Use the existing four-domain/two-tenant fixture plus the separately scoped extra probe required for same-domain/same-host observations; do not silently change its capacity assumptions.

| Test family | Required demonstration on each stack | Packages |
| --- | --- | --- |
| Install/adopt and bootstrap | Selected supported tuple installed/adopted, protected management, recoverable state/trust and verified temporary-service withdrawal | W02–W07 |
| Admission and allocation | Actual entitlement, surviving capacity, quota, reservation, address/name binding; duplicate and conflicting requests | W09–W12 |
| Mandatory isolation | Two tenants remain independent; own-tenant OZ→RZ allowed as designed; unapproved tenant/WSD/same-subnet/same-host and management paths denied | W08, W12, W15 |
| Healthy negative observations | Each denied test has a working source/probe/control path so broken endpoints cannot masquerade as enforcement | W15, W16, W20 |
| Delegated mutation | Actual tenant role cannot remove mandatory groups, alter provider selectors, weaken port security, bypass edge or move into ineligible placement | W09, W15 |
| Forward and return ownership | DNS/time/log/backup/key and workload replies return to the correct origin; connected routes, summaries, NAT/PBR and alternate interfaces cannot create transit | W08, W14, W15 |
| Workload first boot | Correct image/identity/address/storage; effective quarantine before possible power-on; minimal bootstrap connectivity, useful configuration and enrollment | W12–W14 |
| Idempotence and drift | Post-convergence Terraform plan has no unintended change; second Ansible run changes nothing except explicitly justified non-idempotent observations; real drift detected and safely reconciled | W12–W18, W21 |
| Native readback | Full owned-resource mapping, current critical fields, task/entity coverage and unsupported/missing observations handled explicitly | W16 |
| Interrupted execution | Lost reply, stopped runner, late task, stale state/generation, partial apply and concurrent writer; proven scoped fencing before repair/retry | W17, W18 |
| Failure and capacity | Declared host/storage/link/edge/control/service failures, preserved isolation, expected fail-closed behavior and measured surviving capacity | W05–W08, W20 |
| Address families | All offered IPv4/IPv6/dual-stack behaviors, policy/routing parity, local protocols, PMTU, service paths and failure/recovery | W19 |
| Trust lifecycle | Scoped credentials, certificate issuance/renewal/revocation including cache behavior, key outage/recovery and no plaintext fallback | W02, W07, W14 |
| Useful-data recovery | Actual protected capture and isolated restore, verified data integrity/entitlement, catalogue/key dependencies and measured RPO/RTO | W23 |
| Change and upgrade | Resize/growth, patch/reboot, image and provider/platform upgrade, supported replacement and failure recovery | W22 |
| Import and portability | Existing resource adopted without accidental replacement; equivalent declared service re-created on other stacks; data/format/driver limitations recorded | W24 |
| Activation and withdrawal | Required initial readiness before exposure, exact authorized policy/connection changes, real live-path checks, tested withdrawal | W18, W20, W21, W23 |
| Retirement | Early-failure cleanup and normal retirement, dependencies removed, other tenants unaffected, retained data/keys accounted for, delayed address/name reuse | W25 |
| Operational readiness | Alert delivery, on-call and support ownership, incident exercise, recovery runbooks and emergency-change reconciliation | W21, W27 |

An explicitly unsupported operation/profile must be rejected by the execution path and listed in the release offer. “Not applicable” requires the accepted service-scope rationale; it is not a replacement for a failed required test.

## Release checkpoints

| Gate | Required evidence | Remains held when |
| --- | --- | --- |
| G0 — Design/scope | Actual accepted applicability, target tuple, topology, sharing, data/service limits and authorities | Mandatory selection, ownership or support fact is unresolved |
| G1 — Foundation | Commissioned management/fabric/attachments and observed failure/capacity basis | Only installation inventory or an untested topology exists |
| G2 — Offered capabilities | Native campaign, current exact-tuple dossier, supported operations and measured service envelope | Only fixtures, reference strings or empty indexes exist |
| Initial G4 — Operating/recovery readiness | Receiving owner, support/incident readiness, required useful-data restore, recoverable dependencies | Activation would precede its promised initial operating/recovery capability |
| G3 — Controlled activation | Separate current operating/change authority, verified readiness, exposure and withdrawal procedure, live checks | Any required live result is failed or unknown |
| Recurring G4 — Lifecycle assurance | Change/drift/incident/recovery exercises, updated evidence and requalification after material change | Evidence expires, tuple drifts or the service exceeds tested limits |

These gate names follow [the existing commissioning sequence](../native-reference/platform-build.md); this audit does not introduce a second approval model. Git commits and CI success are not substitutes for those authorities.

## Evidence to retain

Bind each native result to the actual site/cell, platform/product/API/provider/hardware/licence tuple, source commit, tool/collection locks, service/profile/address family, operation ID/generation, plan/input digests, native task/resource IDs, timestamps and observation identity. Include expected versus observed outcomes, healthy positive controls, retained failed attempts, artifact digests/freshness, limits, residual gaps and accepting owner.

Keep credentials, raw state/plans, real inventories and sensitive native observations outside this public repository. Maintain private evidence retention and recovery according to the accepted service obligations; publish reviewed summaries and references. Do not use the synthetic Actions artifact retention period as the operating evidence policy by default.

Populate the existing capability, target, provenance, campaign, qualification, capacity and service indexes only from accepted genuine evidence. A record's passing validator proves consistency within its checks; the native action and accepting authority must still exist.

## Documentation-change verification

For this audit, validate documentation navigation, local links, source inventory consistency and repository hygiene. No Terraform/Ansible resource implementation is changed. The audited engine/packet status is recorded separately in [the audit](../../assurance/automation-baseline-audit.md); fresh post-publication CI reports apply to the documentation commit itself.

Future implementation increments must run the existing applicable repository, engine and lab gates, extend tests for their actual new behavior and execute the affected native campaign. Broad synthetic success cannot close an unexecuted native requirement.
