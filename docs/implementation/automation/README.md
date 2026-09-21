# Terraform and Ansible delivery program

**Audit date:** 2026-09-19

**Audited branch/revision:** `main` / `0dff519e852c3e0c72118e04d086548e6f6fd88b`

**Disposition:** End-to-end implementation incomplete; native environments not qualified by the repository evidence.

The repository has useful, tested building blocks for restricted domain, workload and route creation on Nutanix, VMware/NSX and OpenStack. It does **not yet contain a complete Terraform and Ansible process** to commission, provision, configure, activate, operate and retire those environments. Most remaining work is executable integration and native qualification, rather than additional readiness-record validators.

This maintained implementation program carries forward the 1.0 completion plan. Moving it into the documentation hierarchy does not declare the work complete or replace the architecture baseline. The infrastructure architecture, security boundaries and resource ownership remain the basis of the plan.

| Document | Purpose |
| --- | --- |
| [Current package status](progress.md) | Implemented commits, verification and exact remaining work for W01–W29 |
| [WSD deployment](wsd-deployment.md) | Cluster-aware compilation, scoped state identities, domain/workload compositions and output handoffs |
| [Reviewed Terraform execution](terraform-execution.md) | Private saved plans, exact review binding, durable attempts and scope-checked output handoffs |
| [OpenStack bootstrap and withdrawal](openstack-bootstrap.md) | Exact native-ID lifecycle transitions, retained data and narrow service rules |
| [OpenStack workload readback](openstack-readback.md) | Nova placement, Cinder attachments/encryption and Glance image identity |
| [VMware and Nutanix restricted lifecycle](platform-lifecycle.md) | Exact NSX service rules, AHV power/NIC transitions and retained-data withdrawal |
| [NSX domain lifecycle readback](nsx-domain-readback.md) | Owned Tier-1/segment/group/policy snapshots, realization witnesses and held domain plan binding |
| [Nutanix VM readback](nutanix-vm-readback.md) | Scoped AHV placement, membership, disk, NIC and power snapshots; campaign v3 binding |
| [Nutanix Flow readback](nutanix-flow-readback.md) | Owned policy, category/VPC membership and strong-ETag observations; campaign v4 binding |
| [Nutanix Flow task activity](nutanix-flow-activity-readback.md) | Recorded tasks, bounded visible policy work, campaign v4 and held domain lifecycle review |
| [vSphere VM and task readback](vsphere-readback.md) | Exact VM snapshots, child history, template clone source/result witnesses and campaign v5 binding |
| [Held Terraform attempt review](terraform-recovery.md) | Saved-plan configuration/identity checks and private review packets that preserve uncertainty holds |
| [Site commissioning sequence](site-commissioning.md) | Concrete installation-to-recovery campaign and the evidence needed to close native qualification |
| [Reference service decisions](reference-realization.md) | OpenStack-first internal IPv4 qualification path, GitLab state and concrete service products |
| [NetBox IPAM](netbox-ipam.md) | Scoped reserve/confirm/retire operations, conditional writes and lost-response holds |
| [Native guest configuration](native-guests.md) | Bound SSH inventory, candidate Linux roles and native acceptance limits |
| [Guest service profile](guest-services.md) | SSH certificates, resolver ownership, TLS logging and backup enrollment |
| [Encrypted capture and restore](restic-recovery.md) | Real restic exports, independent restore authority and recovered-byte checks |
| [Edge activation and withdrawal](edge-activation.md) | Scoped nftables policy, expiring allows and established-session withdrawal |
| [Target qualification runner](target-qualification.md) | Actual API readback and pinned guest probes with healthy denial controls |
| [Repository audit](../../assurance/automation-baseline-audit.md) | Verified implementation inventory, concrete gaps and exact-revision CI evidence |
| [Environment coverage](environments.md) | Completion requirements for all three platform families, common infrastructure, lifecycle environments and optional service profiles |
| [Cluster topology and WSD placement](../../engineering/cluster-topology-and-wsd-placement.md) | Proposed physical/control/service cluster roles, shared versus dedicated capacity, and WSD placement across primary and recovery infrastructure |
| [Required delivery process](delivery-process.md) | How Terraform, Ansible, supported installers and service-owner tools must work together from bootstrap through retirement |
| [Completion backlog](completion-backlog.md) | Prioritized work packages, dependencies, proposed owner roles, deliverables and closure criteria |
| [Acceptance and release gates](acceptance.md) | Tests and evidence required before calling each environment complete |
| [Repository release controls](release-controls.md) | Proposed required reviews/checks, administrator prerequisites and release sequence |
| [Audit snapshot](../../assurance/automation-baseline-evidence.json) | Machine-readable source inventory and observed CI metadata for this audit |

## Main gaps

1. Build the P0–P3 foundation: recoverable automation/state, physical fabric/OOB, platform installation and security/shared-service integrations.
2. Qualify the new Terraform WSD compositions and connect actual entitlement, quota, capacity/IPAM/DNS and security-edge handoffs. Cluster-aware draft compilation is implemented.
3. Qualify the new bound Linux guest profile and complete selected image/first-boot, OS hardening, service enrollment, Windows/other offered profiles and operations. Local validation remains separate.
4. Connect native restricted bootstrap and edge attachments to the implemented expiring activation/withdrawal adapter. Qualify boot/HA containment and permitted service paths. Existing quarantine defaults must remain effective until prerequisites are verified.
5. Complete readback, drift, interrupted-operation reconciliation, upgrades, import/adoption, restore, migration and data-safe retirement across all three stacks.
6. Execute real native qualification campaigns and record actual accepted capacity, recovery and operational evidence. Current successful CI does not close these items.

## Scope of “all environments”

The core platform scope is **Nutanix AHV/Flow, VMware vSphere/NSX and OpenStack**. Completeness also includes their shared foundation and provider services, and each declared lifecycle target such as qualification, non-production, production and recovery. The repository contains no populated deployment inventory proving those lifecycle targets exist. Public hosting, additional address families and future platform extensions need explicit scope decisions and their own qualification; they cannot silently inherit the internal OZ/RZ fixture's results.

The first implementation target should be the existing two-tenant internal OZ/RZ reference fixture, completed vertically on one selected supported stack, then reproduced and qualified on the other two. The overall three-stack milestone remains open until each stack meets the same declared service outcomes.

The baseline audit remains historical. Follow [implementation progress](progress.md) for current code delivery and remaining native dependencies. Actual tuple selection, qualification and operating authority remain separate from code publication.

[Documentation home](../../README.md)
