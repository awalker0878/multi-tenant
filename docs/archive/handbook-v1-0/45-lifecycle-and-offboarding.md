# 45. Lifecycle and Offboarding

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Deletion is a security workflow, not simply terraform destroy. The controller must remove connectivity, identities, certificates/secrets, DNS, service bindings, public exposure, routes, policies and inventory records while preserving required logs and backup retention evidence.

14. Set WSD to Retiring and prevent new optional dependencies.

15. Identify dependent services, DNS, certificates, backup/retention requirements, and external integrations.

16. Withdraw public ingress and discretionary egress.

17. Remove/expire application flows and service bindings in dependency-safe order.

18. Stop workloads and confirm required backup/retention state.

19. Destroy workload and network resources.

20. Withdraw prefixes/routes and release addresses through IPAM quarantine policy.

21. Revoke identities, secrets, certificates and automation grants.

22. Generate destruction evidence and close inventory/CMDB records.


<a id="source-table-347"></a>

| LIFE-001 | Offboarding SHALL remove obsolete routes and policy objects and SHALL produce evidence of completion. |
| --- | --- |

[Previous chapter](44-change-and-exception-management.md) · [Chapter index](README.md) · [Next chapter](46-migration-and-transition-connectivity.md)
