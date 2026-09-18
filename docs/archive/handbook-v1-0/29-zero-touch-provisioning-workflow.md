# 29. Zero-Touch Provisioning Workflow

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
![Image: image7.png](../../assets/diagrams/f09d6be7f3902583cf2d.png)

Figure 8. Provisioning is complete only after realization, testing, and evidence.

1. Receive a versioned WSD request from a service catalogue or API.

2. Validate schema, naming, ownership, quotas, and lifecycle metadata.

3. Apply security admission rules to zone topology, exposure, required services, and requested flows.

4. Allocate IPv4/IPv6 prefixes and reservations from authoritative IPAM.

5. Compile route intent through the Route Authority.

6. Evaluate platform capabilities, security authorization, site constraints, capacity, lifecycle and availability.

7. Select the platform adapter and construct the Terraform root stack.

8. Run terraform plan and policy-as-code checks; require approval where the change class requires it.

9. Apply using a least-privileged execution identity.

10. Wait for platform realization/readiness rather than treating API acceptance as completion.

11. Run security, route, reachability, logging and negative-path tests.

12. Generate evidence and register the realized service in inventory/CMDB.

13. Mark the WSD Service Ready only when mandatory gates pass.


<a id="source-table-248"></a>

| AUTO-001 | If security admission, IPAM, route authority, or mandatory policy validation is unavailable, new provisioning SHALL stop rather than inventing or bypassing required state. |
| --- | --- |

[Previous chapter](28-canonical-hosting-api.md) · [Chapter index](README.md) · [Next chapter](30-terraform-architecture.md)
