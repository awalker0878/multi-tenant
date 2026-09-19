# 1.0 — Terraform and Ansible completion audit

**Audit date:** 2026-09-19

**Audited branch/revision:** `main` / `0dff519e852c3e0c72118e04d086548e6f6fd88b`

**Disposition:** End-to-end implementation incomplete; native environments not qualified by the repository evidence.

The repository has useful, tested building blocks for restricted domain, workload and route creation on Nutanix, VMware/NSX and OpenStack. It does **not yet contain a complete Terraform and Ansible process** to commission, provision, configure, activate, operate and retire those environments. Most remaining work is executable integration and native qualification, rather than additional readiness-record validators.

This folder records the work needed for a 1.0 delivery. The folder name is a planning milestone, not a release declaration or a replacement for the existing architecture v1.4 baseline. The infrastructure architecture, security boundaries and resource ownership remain the basis of the plan.

| Document | Purpose |
| --- | --- |
| [Repository audit](audit.md) | Verified implementation inventory, concrete gaps and exact-revision CI evidence |
| [Environment coverage](environments.md) | Completion requirements for all three platform families, common infrastructure, lifecycle environments and optional service profiles |
| [Required delivery process](delivery-process.md) | How Terraform, Ansible, supported installers and service-owner tools must work together from bootstrap through retirement |
| [Completion backlog](completion-backlog.md) | Prioritized work packages, dependencies, proposed owner roles, deliverables and closure criteria |
| [Acceptance and release gates](acceptance.md) | Tests and evidence required before calling each environment complete |
| [Audit snapshot](audit-evidence.json) | Machine-readable source inventory and observed CI metadata for this audit |

## Main gaps

1. Build the P0–P3 foundation: recoverable automation/state, physical fabric/OOB, platform installation and security/shared-service integrations.
2. Compose the existing independent Terraform roots into repeatable tenant/WSD deployments with actual entitlement, quota, placement, IPAM and DNS handoffs.
3. Add remote Ansible inventories and roles for supported guest/platform configuration, hardening, service enrollment and operations. The current two playbooks operate only on localhost.
4. Implement restricted bootstrap, security-edge attachments, permitted service paths and a separately controlled activation/withdrawal process. Existing quarantine defaults must remain effective until prerequisites are verified.
5. Complete readback, drift, interrupted-operation reconciliation, upgrades, import/adoption, restore, migration and data-safe retirement across all three stacks.
6. Execute real native qualification campaigns and record actual accepted capacity, recovery and operational evidence. Current successful CI does not close these items.

## Scope of “all environments”

The core platform scope is **Nutanix AHV/Flow, VMware vSphere/NSX and OpenStack**. Completeness also includes their shared foundation and provider services, and each declared lifecycle target such as qualification, non-production, production and recovery. The repository contains no populated deployment inventory proving those lifecycle targets exist. Public hosting, additional address families and future platform extensions need explicit scope decisions and their own qualification; they cannot silently inherit the internal OZ/RZ fixture's results.

The first implementation target should be the existing two-tenant internal OZ/RZ reference fixture, completed vertically on one selected supported stack, then reproduced and qualified on the other two. The overall three-stack milestone remains open until each stack meets the same declared service outcomes.

This audit adds documentation only. It does not select an actual product tuple, create an environment, issue operating authority or change existing automation safeguards.

[Documentation home](../README.md)
