# Required end-to-end Terraform and Ansible process

[1.0 index](README.md) · [Completion backlog](completion-backlog.md) · [Acceptance gates](acceptance.md)

## Ownership and execution model

Use the existing [P0–P6 infrastructure work packages](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md). A supported installer commissions a platform; Terraform manages its accepted resource scopes; Ansible configures supported host/guest/service scopes and runs operational procedures; service owners retain address/name, edge, identity/key and protection authority. The coordinator may be an existing automation/change platform. Building a custom controller, API or database is not a prerequisite.

| Scope | Primary writer | Required handoff |
| --- | --- | --- |
| Hardware, OOB, physical fabric | Selected hardware/network automation | Accepted devices, interfaces, routing/attachment capacity, failure envelope and management access |
| Platform installation/upgrade | Supported vendor/distribution lifecycle tool, optionally invoked through Ansible | Installed tuple, cluster health, eligible compute/storage/overlay pools and protected APIs |
| Tenant/domain/VM/volume native resources | Qualified Terraform root or explicitly assigned native tool | Exact resource identities, generation, applied plan and verified state |
| Guest OS configuration | Ansible and approved image initialization, with non-overlapping ownership | Guest identity, baseline/configuration version, service enrollment and health |
| Edge, DNS/IPAM, IAM/PKI/KMS, backup | Respective service-owner integration | Scoped resource/service binding, readiness and lifecycle receipt |
| Verification | Separate readback and packet/data observations where required | Evidence bound to actual target, operation, source revision and time |

Do not use Ansible shell commands to compete with Terraform for the same native VM, route or policy fields. Do not use Terraform to write directly to a backend already owned by a platform API. Define field/resource ownership before code is added.

## Required sequence

The following is the **target implementation**, not a command sequence currently provided by the repository.

| Stage | Required execution | Outputs and gate | Failure behavior |
| --- | --- | --- | --- |
| 0. Select and prepare | Accept site/tuple/service scope, LLD, version support, identities, data restrictions and allowed operations; prepare private input/evidence locations | Reviewed target and bounded authority; no `.invalid` or invented native IDs | Stop before native contact when target or authority is unresolved |
| 1. Bootstrap P0 | Recoverable runner, trust/time/name dependencies, credential custody and state service | Independent management and recoverable state/secrets; temporary dependencies recorded | Preserve independent recovery path; never broaden egress to bootstrap |
| 2. Commission P1–P3 | Physical fabric/OOB, platform installer, storage/overlay, edge and foundation services using their owners' tools | Observed health, eligible capacity, service interfaces; restricted campaign can proceed before ordinary placement qualification | Contain partial work and reconcile actual resources |
| 3. Qualify capacity | Run the restricted reference fixture and native failure/recovery campaign | Accepted tuple/capabilities, G1/G2 evidence and commissioned service envelope | No ordinary tenant placement on failed/unqualified capacity |
| 4. Admit ordinary allocation | Validate tenant entitlement, WSD zones/placement, capacity and requested offer; reserve capacity, allocate addresses and register intended dependencies | Stable operation/generation, current envelope binding and authoritative reservation/IPAM receipts | Uncertain allocation holds; do not guess a free address or duplicate a reservation |
| 5. Prepare plans | Resolve only accepted upstream IDs, initialize correct backend, create per-owner plans and review change/replacement scope | Protected saved plans, input/source/lock digests and approval bound to the plan | Refuse stale state, changed input, expired evidence or unapproved replacement |
| 6. Build denied domains | Apply accepted Terraform domain/quarantine scopes; configure edge attachment as separately owned | Native policy/membership/placement readback and actual denial observations before workload connection | Preserve containment; do not continue on a reference string alone |
| 7. Build and configure workloads | Create native resources, publish bounded inventory, permit narrowly scoped bootstrap, initialize guest and run Ansible roles | Healthy guest, correct identity/address/storage, OS baseline and service enrollment; second run converges | No production path; partial guest/native state recorded and recoverable |
| 8. Bind required services | Complete DNS, time, PKI/KMS, telemetry, image/package, storage and backup bindings; verify both directions and entitlements | Required current trust/storage/backup/bootstrap/reply evidence | Required service failure holds activation; no unrestricted fallback |
| 9. Verify and activate | Validate native state, permitted and denied paths, useful-data restore and operational readiness; execute separately authorized exposure/policy transition | G0/G1/G2 and applicable initial G4, current G3 authority, live post-activation evidence | Withdraw exposure on failed or unknown live verification and retain evidence |
| 10. Operate and change | Observe drift, plan updates, rotate credentials, patch/upgrade, resize, repair and requalify changed capabilities | Current as-built, state, inventory, support and service evidence | Incident containment outranks ordinary desired-state convergence |
| 11. Recover or retire | Fence writers, isolate recovery, prove data consistency; withdraw service, clean dependencies and transfer retained-copy/key duties | Measured recovery or resource-by-resource retirement receipts | Never release addresses/names/capacity while ownership or dependent cleanup is unknown |

Cleanup is possible after any failed native stage under the previously accepted scope and cleanup authority. It must not depend on successful qualification or production activation. Initial restricted qualification must not require an already qualified copy of the capability under test; routine allocation does require qualified capacity.

## Terraform composition to build

1. Introduce thin, per-platform environment compositions or ordered root execution using the existing module boundaries. Keep foundation, security-edge, tenant/domain and workload state separate wherever authority/lifecycle differ. Avoid a single estate-wide state.
2. Define a reviewed state-key convention using site/cell, platform, lifecycle target, owner scope and stable tenant/WSD/domain identity as applicable. Bind the backend and credential scope to that identity; avoid selecting production merely by a mutable workspace name.
3. Provision the selected HTTP-compatible backend or deliberately adopt another supported backend. Demonstrate authenticated access, locking/concurrency, encryption, versioning, backup and recovery. An empty `http` block supplies none of those service guarantees.
4. Publish minimum accepted outputs to the next owner. Existing `handoff` outputs are a starting point; they need exact target/generation, resource mapping, observations and lifecycle state. Avoid broad access to other owners' state just to obtain an ID.
5. Save and review exact plans; protect plans/state as sensitive. Reject unintended deletion/replacement and changes to mandatory isolation. Replan after any material input/state/source/approval change.
6. Add explicit desired-state transitions for prepared, restricted bootstrap, configured, verified, activated, contained and retiring resources. The current hard-coded disconnected/down/off settings would otherwise be reasserted on later applies after an out-of-band activation. Each field must continue to have one owner.
7. Supply approved import/adoption, moves, upgrades, replacements and retention-aware retirement procedures. `prevent_destroy` is retained as a safeguard; removing it is not the implementation of safe retirement.

## Ansible implementation to build

| Role/procedure family | Required responsibility | Verification |
| --- | --- | --- |
| Preflight and inventory | Validate target identity, privilege, reachability, source/tuple, inventory generation and required handoffs | Wrong target, stale handoff or excess privilege rejected before mutation |
| Platform installer adapters | Invoke supported idempotent installation/configuration interfaces; retain task IDs and receipts | Fresh install/adoption and interrupted-operation resume tested per selected release |
| Guest baseline | Supported Linux/Windows variants as selected, access controls, time/resolver, firewall, audit, patching and reboot handling | Real guest convergence, second-run idempotence, safe check mode and drift repair |
| Trust and enrollment | Actual PKI/IAM/key/log/monitoring/backup/image-service consumption under scoped authority | Rotation/revocation, dependency outage and removal of temporary enrollment privileges |
| Verification | Native observer dispatch plus service/path/data checks | NSX, Nutanix and Neutron parity; additional compute/storage observers and healthy positive controls |
| Operations | Patch, upgrade, certificate rotation, scale/repair, restore and retirement procedures | Bounded batches, maintenance windows, failure stops and preserved incident restrictions |

Use versioned inventories and safe templates in Git; source real target IDs/endpoints and credentials from approved private systems. Bind inventory to native receipts rather than discovering arbitrary reachable hosts. Restrict privilege escalation to the roles that need it. Add pinned collections and an execution environment whose tool versions match the qualification evidence.

Keep the current local-only playbooks intact as a distinct test profile. Introduce separately validated remote/native profiles and update the repository checker deliberately; globally relaxing the localhost guard would remove an existing boundary without replacing it.

## Execution and evidence integration

Separate PR checks, native qualification and production execution. PR jobs keep no-contact fixtures and no live credentials. Native jobs use scoped runners, protected environment inputs, exact targets, current authority and separate read/write identities where required. The workflow must check current time for live validity; the fixed `--as-of` timestamps in synthetic CI examples are deterministic fixture inputs, not live authorization checks.

Serialize writers by actual owned resource scope across Terraform, Ansible and service integrations. Preserve operation IDs and native task identities on retries. An expired coordinator lease or released Terraform lock does not fence a still-running native task. On uncertainty, reconcile first; use [the existing recovery reasoning](../implementation/native-reference/recovery-retirement.md) to guide a real owner-operated implementation.

Retain raw plans/state/logs/native evidence privately with appropriate access and retention. Publish only reviewed, non-sensitive evidence references and digests to Git. The current public CI artifacts and 14-day retention are suitable for synthetic checks, not automatically for native operational evidence.
