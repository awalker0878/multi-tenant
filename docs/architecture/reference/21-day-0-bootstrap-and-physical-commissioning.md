# 21. Day-0 bootstrap and physical commissioning

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3680_865363315"></a>
<a id="RA_s_021"></a>

An empty site cannot be provisioned by assuming that the platform APIs, identity service, DNS, certificate trust and Terraform state backend already exist. Day 0 establishes a minimum trusted management and recovery path first. The bootstrap procedure has an accountable owner, a restricted temporary execution environment, verified artifacts and a recorded handover to steady-state management.


<a id="source-table-304"></a>

| Order | Bootstrap or foundation activity | Exit condition |
| --- | --- | --- |
| 1 | Confirm site resources, power/fault domains, supported hardware, cabling roles and secure staging | Inventory and physical design accepted; no unassigned default-access device exposed |
| 2 | Establish restricted console/OOB and initial administrator trust | Authorized hardware access exists independently of tenant networks |
| 3 | Provide minimum trusted name/time, identity or controlled emergency access, certificate trust and artifact access | Required management dependencies available; temporary credentials and exceptions recorded |
| 4 | Prepare protected automation execution and configuration/state recovery | Verified tooling, scoped network access, encrypted records and recoverable bootstrap material |
| 5 | Commission transport routing, multihoming, platform transport and physical service attachments | Routing, MTU, failure and management-isolation checks pass |
| 6 | Hand over the physical foundation to its steady-state owner | Configuration source, inventory, credentials, monitoring and safe maintenance procedure accepted |

Use supported switch/hardware configuration interfaces and platform installation methods. Terraform may manage a resource once its relevant API/provider capability is qualified; it is not assumed to configure every switch operating system or install every hypervisor. A provider coverage gap must be recorded with its supported alternative, owner, error handling and evidence. An arbitrary command embedded in a Terraform run does not become a supported declarative resource merely because the run exits successfully.

Bootstrap services may be temporarily external to the new hosting cell. Their location, access scope, lifetime and transition are documented. When steady-state identity, names, keys and automation are established, migrate ownership without losing recovery access, revoke temporary grants and reconcile configurations. Do not destroy the only recovery material as part of a bootstrap cleanup step.

The [bootstrap service assurance gate](../../engineering/bootstrap-service-readiness-assurance.md) records the exact authoritative address/name lifecycle, minimum dependency, restricted-management, dependency-loss and steady-state transition evidence required before this bootstrap profile can be treated as current. It does not perform any bootstrap mutation.

## Foundation changes after Day 0

Adding hosts, new attachment pools, service leaves or another cell follows the same foundation controls without becoming an ordinary tenant operation. Drain or isolate affected resources, verify compatibility and surviving capacity, apply the approved change and requalify impacted paths. A new switch or host is not eligible simply because its management API is reachable. It becomes eligible after its baseline, inventory and operational ownership are accepted.

The commissioning record includes the physical topology, device and firmware inventory, management dependencies, addresses/ASNs, allowed interfaces/neighbours, MTU budget, backup configuration, test evidence and explicit limitations. Those are the inputs Terraform and other provisioning tools consume; they are not values that a workload request invents.

Related engineering: [PROV §2 — Day-0 and steady-state commissioning without circular dependencies](../../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md#PROV_s_002)

[Previous chapter](20-provisioning-model-and-infrastructure-work-packages.md) · [Chapter index](README.md) · [Next chapter](22-vendor-platform-and-shared-service-commissioning.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0014 — Bootstrap management and trust before consuming native APIs](../../adr/0014-bootstrap-management-and-trust-before-consuming-native-apis.md)

<!-- END GENERATED DECISION LINKS -->
