# Q05 — Native provisioning

Q05 verifies R07–R08, R18–R21 and R25, with R16/R17 execution and allocation safeguards. It supports P07.01–P07.06 and G07.01–G07.04. This campaign qualifies the selected OpenStack provision/activate/retire path; migration and additional platforms require separate campaigns.

## Scope and ownership

Platform and service owners authorize their bounded resource/API scopes. Lifecycle coordinates effects; the application owner verifies useful service; qualification independently observes native outcomes. E3 requires the exact commissioned OpenStack tuple, guest image, storage/network/security topology and product artifacts. A passing simulated adapter cannot satisfy this campaign.

Use the [application walkthrough](../../product/application-walkthrough.md), [support matrix](../../implementation/support-matrix.md), [deployment model](../../operations/deployment-model.md) and [Q06 policy procedure](q06-policy-equivalence.md). Service owners must select actual DNS/IPAM, identity, time/trust, logging, monitoring and backup contracts; example vendor names confer no integration support.

## Preparation

1. Confirm the applicable G06 outcomes and Q04 fault procedures for the release under test.
2. Commission exact endpoints, native quotas/capacity, management/transport, failure domains, trust, restricted credentials and independent observer access.
3. Establish campaign-specific authority, impact budget, stop/revocation, separate retirement scope and retention rules.
4. Pin reviewed saved plan, Terraform state/backend identity, provider/worker images, guest hardening and application fixture manifest.
5. Verify quarantine paths, approved policy probes, service owner receipts and an isolated restore destination before native writes.

## Case matrix

| Case | Action or injected fault | Required observation | Evidence |
| --- | --- | --- | --- |
| Q05.01 | Admit and prepare the exact plan, then present an uncommissioned site or widened endpoint/resource scope | Valid campaign proceeds within limits; uncommissioned/widened scope is denied before effects | Admission and commissioning comparison |
| Q05.02 | Reserve capacity/IP/service allocations, including one partial owner failure | Authoritative receipts match journaled scope; partial results are held/reconciled without double allocation | Owner receipts and independent allocation observations |
| Q05.03 | Apply the saved plan for multi-workload, disk and NIC mappings | Only owned scoped resources appear; ordering, state identity, placement and mappings match the reviewed plan | Saved-plan digest, state identity and native resource readback |
| Q05.04 | Boot and configure the selected guest profile in quarantine | Boot, device mapping, guest identity/hardening and readiness pass; no application traffic is exposed early | Guest observations, hardening report and quarantine probes |
| Q05.05 | Enroll DNS/IPAM, identity, time/trust, logging, monitoring and backup | Actual service/reply paths work; owner receipts and expected records match scoped resources | Service checks, receipts and correlated observations |
| Q05.06 | Restore the synthetic database/attachments into isolated validation scope | Application checks, record relationships, metadata and attachment digests match the accepted recovery objective | Backup/restore identities and data comparison |
| Q05.07 | Activate after Q06 checks; then deny a required service/policy precondition | Valid activation permits declared application tasks; failed precondition keeps traffic contained | Ordered readiness/activation observations and denial |
| Q05.08 | Lose apply response, crash worker, revoke authority or fail activation | Unknown/partial work remains held; Q04 reconciliation and approved restore recover without uncontrolled writes | Native fault dossier and reconciled journal/state |
| Q05.09 | Submit a managed change with fresh approval, then inject ownership collision or drift | Only approved owned fields change; collision/drift blocks unsafe mutation and preserves evidence | Plan diff, native comparison and conflict holds |
| Q05.10 | Retire under separate authority; attempt deletion with provisioning approval or unresolved retention | Only permitted owned resources are removed; required data/keys remain; allocations release after confirmed absence | Retirement approval, retention decision and deletion/release receipts |

## Execution and observations

Observe native state independently after each important boundary: allocation, domain/network binding, compute creation, guest readiness, service enrollment, activation and deletion. A completed automation process is insufficient when the application cannot authenticate, read/write data or receive protection/monitoring.

Execute policy checks at the actual same-host, subnet and edge topology using Q06. Preserve separate source IDs for command response, native resource, managed binding, state version and observation generation.

If hardening or service configuration fails, keep the application in quarantine and retain the failure record. Recovery uses approved resource scope; cleanup must not remove shared or previously existing infrastructure.

## Pass criteria and evidence

The whole selected application path must pass, including service readiness, restore, traffic isolation, failure containment and separate retirement authority. No missing mandatory service may be treated as a successful partial activation. Publish only the tested topology and profile bounds.

Collect native tuple/artifact identities, plan/state digests, owner receipts, guest/service checks, Q06 references, data restore results and independent retirement observations. Bind each outcome to G07 criteria using the [evidence rules](../../implementation/status-model.md).

## Cleanup and reruns

Use the tested retirement procedure to remove only campaign-owned resources and confirmed unused allocations. Preserve retained data/keys and dossier records. Repeat affected cases after native/provider/guest/service/enforcement changes; provisioning evidence does not automatically qualify a different operation or migration method.
