# Repository audit — actual coverage and remaining gaps

[1.0 index](README.md) · [Environment coverage](environments.md) · [Completion backlog](completion-backlog.md)

## Baseline and method

Reviewed `main` at [`0dff519e852c3e0c72118e04d086548e6f6fd88b`](https://github.com/awalker0878/multi-tenant/tree/0dff519e852c3e0c72118e04d086548e6f6fd88b) on 2026-09-19. Inspected all ten Terraform modules and corresponding roots, their provider pins/locks and mock-test scope; both Ansible playbooks and roles; the three workflow definitions; native observer/recovery/DNS tooling; capability and assurance indexes; and current architecture, commissioning and lifecycle documentation. No native platform was contacted or changed during this audit. External systems may contain additional implementations or evidence; none is credited without an accepted repository handoff.

Findings concern the inspected source revision. Relative source links make navigation convenient; use the pinned revision above when comparing a later implementation. Provider versions below describe committed code, not newly verified vendor compatibility or recommendations to install those versions.

## Evidence already present

| Item | Verified state at the audited revision | Practical meaning |
| --- | --- | --- |
| Terraform structure | 10 native module/root pairs, 10 root lock files, plan-only module mock suites | Real provider resource definitions exist; this is more than pseudocode |
| Terraform state | Every root declares an empty HTTP backend configuration | Backend selection, access, locking, state separation, backup and recovery still need an operational implementation |
| Terraform inputs | Disabled restricted-build examples; native IDs supplied by callers | Roots assume upstream platform, identity, image, placement, storage and attachment handoffs |
| Terraform safeguards | Restricted-build opt-in, external reference preconditions, quarantine settings and `prevent_destroy` | Useful safeguards; reference strings are not authenticated approvals and lifecycle protection is not a retirement process |
| Ansible | 2 localhost playbooks, 2 local roles and one localhost inventory | Local handoff staging and input validation are implemented; remote configuration is not |
| Observers | NSX, Nutanix and Neutron read-only tools; bounded explicitly recorded Nutanix task-tree support | Reusable partial readback; no complete infrastructure inventory, writer fencing or repair executor |
| DNS | RFC2136 transaction client and disposable DNS tests | A bounded write path exists; authoritative IPAM and the full service-owner workflow are still separate |
| Assurance | Extensive validators for native qualification, capacity, reservations, address/name, trust, edge, recovery and operating evidence | Validation of supplied records does not supply the live service or generate genuine acceptance evidence |
| Active readiness evidence | All 20 `sources/capabilities/*index.json` files have empty `records`; all 3 platform tuples are `UNSELECTED` and all 30 registered capability entries are `NOT_QUALIFIED` | The repository cannot establish any of the three stacks as ready for ordinary placement |

Sources: [Terraform](../../terraform/README.md), [Ansible](../../ansible/README.md), [capability registry](../../sources/capabilities/platform_registry.json), [capability indexes](../../sources/capabilities/), [native reference procedure](../implementation/native-reference/platform-build.md), [audit snapshot](audit-evidence.json).

## Exact-revision CI

The GitHub run and job metadata below was read during the audit. Both runs target the audited SHA. Completed job steps include actual engine validation and the routed laboratory checks. Artifact payloads were not independently downloaded and re-audited for this documentation task.

| Workflow / job | Observed conclusion | What the configured job proves |
| --- | --- | --- |
| [Architecture and automation validation](https://github.com/awalker0878/multi-tenant/actions/runs/35461586998) — repository | Success | Repository/documentation checks, Python regressions, held readiness examples and local task-tree fixture |
| Same run — [Terraform](https://github.com/awalker0878/multi-tenant/actions/runs/35461586998/job/105946307366) | Success | Provider lock review, backend-disabled initialization/validation and plan-only provider mocks |
| Same run — [Ansible](https://github.com/awalker0878/multi-tenant/actions/runs/35461586998/job/105946307395) | Success | Syntax, local staging, local idempotence/check mode, negative cases and no-contact manifest validation |
| [Routed IPv6 laboratory](https://github.com/awalker0878/multi-tenant/actions/runs/35461586988) | Success | Disposable Linux IPv4/IPv6 paths, denials, replies and recovery; exact-source report validation |

Do not repeat the old ZIP-era “engine blocked/not run” wording in the Terraform/Ansible READMEs as the current CI result. Conversely, successful CI is not a native deployment, a native IPv6 qualification, an isolated platform restore or production readiness. The [workflow](../../.github/workflows/validate.yml) deliberately verifies many **HOLD** outcomes with empty active evidence.

## Terraform coverage by owned scope

Every source link below points to the actual module. Matching standalone roots live under [terraform/roots](../../terraform/roots/). No root composes the complete fixture or the full P0–P6 process.

| Module | Native resources currently implemented | Material work still outside this module |
| --- | --- | --- |
| [nutanix-domain](../../terraform/modules/nutanix-domain/main.tf.json) | Category, regular VPC, IPv4 overlay subnet, enforced application/intra-group quarantine | Project/RBAC, commissioned platform, external attachments, full permitted policy, edge integration and IPv6 service |
| [nutanix-workload](../../terraform/modules/nutanix-workload/main.tf.json) | VM, image-based boot disk, optional data disk, category/project binding, fixed IPv4 NIC; VM off and NIC disconnected | Guest bootstrap, accepted connection/power transition, identity/services, eligible placement validation and operational acceptance |
| [nutanix-route](../../terraform/modules/nutanix-route/main.tf.json) | Exact static IPv4 route through a supplied external subnet reference | Creation/qualification of external subnet, receiving edge, attachment, return path and failover |
| [nsx-domain](../../terraform/modules/nsx-domain/main.tf.json) | Distributed Tier-1, disconnected segment, membership group, emergency distributed DROP policy | Upstream/Edge/Tier-0 construction, tenant authority, admitted connections and complete security-edge outcomes |
| [vsphere-workload](../../terraform/modules/vsphere-workload/main.tf.json) | VM clone, boot/optional data disk, supplied resource pool/datastore/storage policy and quarantine network | Platform pools/templates, guest configuration, connected lifecycle and reliable vSphere compute/storage readback |
| [nsx-route](../../terraform/modules/nsx-route/main.tf.json) | Exact IPv4 static route on a supplied gateway | Gateway construction, upstream isolation, HA routing, service-side return path and route lifecycle coordination |
| [nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) | Scoped emergency gateway DROP policy | Gateway/edge installation, attachments, qualified permitted policy and controlled exposure |
| [openstack-domain](../../terraform/modules/openstack-domain/main.tf.json) | Private network, IPv4 subnet, router/interface, security group without default rules; network/router down and DHCP off | Keystone project/RBAC/quotas, mandatory policy ownership, selected DHCP/metadata, external gateway and supported IPv6 |
| [openstack-workload](../../terraform/modules/openstack-workload/main.tf.json) | Disabled explicit port, boot/data Cinder volumes, shutoff Nova server and optional volume attachment | Image/flavor/AZ provisioning, guest configuration, ready-state transition, storage/key/backup enrollment and placement qualification |
| [openstack-route](../../terraform/modules/openstack-route/main.tf.json) | Exact router route | External boundary, enforced routing-policy ownership, return path and HA/failure qualification |

Important platform asymmetry: the [vSphere module](../../terraform/modules/vsphere-workload/README.md) explicitly does **not** promise powered-off staging. It may power on during cloning and relies on independently verified quarantine before creation. A cross-platform pipeline must preserve this difference instead of assuming all three workload modules are inert until a later power-on step.

Committed provider pins are Nutanix `2.4.2`, NSX `3.10.0`, vSphere `2.12.0` and OpenStack `3.4.0`. The CI Terraform engine is `1.13.5`; module constraints accept `>= 1.7.0, < 2.0.0`. These versions need an accepted installed product/API/hardware/licence tuple and a tested upgrade policy before native use.

## Ansible coverage and integration gaps

| Source | Implemented behavior | Missing for complete delivery |
| --- | --- | --- |
| [stage_reference.yml](../../ansible/playbooks/stage_reference.yml) / [configuration_bundle](../../ansible/roles/configuration_bundle/tasks/main.yml) | Validate a local engineering fixture and render private JSON/CSV files into a marked staging directory | Actual platform/host/network/guest configuration and accepted output-to-inventory handoff |
| [validate_readback.yml](../../ansible/playbooks/validate_readback.yml) / [readback_validate](../../ansible/roles/readback_validate/tasks/main.yml) | Validate NSX or Nutanix manifests without target contact | Neutron dispatch parity, approved native readback workflow, complete workload/storage coverage and live acceptance |
| [localhost inventory](../../ansible/inventories/localhost.yml) | Fixed local execution, no facts/escalation | Isolated inventory sources, target identity checks, Linux SSH / Windows WinRM or PSRP where offered, credential injection and remote role tests |
| [requirements-dev.txt](../../requirements-dev.txt) | Pinned Ansible core and selected Python dependencies | Selected vendor collections, collection dependency locks, reproducible execution environment and native version qualification |

The local staging role's second-run idempotence is valuable, but it does not establish idempotence of any future remote installer, guest hardening role or service enrollment operation.

## Findings and completion implications

| ID | Finding | Evidence | Work packages |
| --- | --- | --- | --- |
| F01 | No executable P0–P3 commissioning chain | [Current TAD open work](../current/TAD-infrastructure.md), [native platform build procedure](../implementation/native-reference/platform-build.md) | W01–W08 |
| F02 | Partial roots are not an environment deployment composition | Ten independent roots with supplied upstream IDs and `handoff` outputs | W03, W09, W12, W18 |
| F03 | No remote Ansible provisioning/configuration path | Both playbooks fix localhost; only two local roles | W04, W13–W14 |
| F04 | No integrated admission/reservation/IPAM/DNS mutation sequence | Preflight validators and empty indexes; [DNS client](../../tools/dns_change.py) is a separate bounded mechanism | W10–W12 |
| F05 | Quarantine exists but complete ZIP, approved connectivity and activation execution do not | Domain/workload defaults, route scope and [activation gate](../engineering/production-activation-and-initial-readiness-assurance.md) | W08, W15, W18–W20 |
| F06 | Native readback is partial; no actual fencing/reconciliation executor | [Observers](../implementation/code-map.md), [recovery reviewer](../../tools/recovery_review.py), [task-tree support](../../tools/nutanix_task_tree.py) | W16–W18 |
| F07 | Service integrations are mostly specifications and evidence validators | [Foundation interface schedule](../implementation/native-reference/service-interfaces.md), empty service indexes | W07–W08, W10–W15 |
| F08 | Native create/change/recovery/retirement have not been demonstrated across the three stacks | No native dossiers/campaign evidence; [recovery procedure](../implementation/native-reference/recovery-retirement.md) is a procedure, not an executor | W17, W20–W25 |
| F09 | Current CI is intentionally unable to deploy native environments | [Repository checker](../../scripts/check_repository.py) rejects remote playbooks in the current path and native/secret-bearing workflow commands | W04, W18, W26 |
| F10 | Address-family/public/extension scope is incomplete | Registry IPv6 entries are local fixtures; [public profile](../current/public-hosting-design-profile.md) is proposed; extension index empty | W01, W19, W28–W29 |
| F11 | Historical status text can obscure genuine progress | Terraform/Ansible README authoring limitations versus successful exact-revision jobs | W27 |

F09 is an intentional current boundary, not a reason to disable checks. A future implementation must explicitly introduce separate native execution profiles and validate them while preserving the no-contact behavior of ordinary PR validation. The Terraform verifier also hard-codes a ten-module/ten-root completion count, so adding modules requires updating the inventory-driven validation design under W26.

## Overall assessment

This is a substantial architecture, bounded automation and assurance foundation. It is not yet an operational multi-environment provisioning system. No defensible completion percentage follows from document volume, validator count or passing CI. Track closure by executable work packages and native outcomes in [the backlog](completion-backlog.md) and [acceptance matrix](acceptance.md).
