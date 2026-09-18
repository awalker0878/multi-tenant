# Appendix G — Operational records and decision templates

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13445_1645000677"></a>
<a id="app_G"></a>

<a id="__RefHeading___Toc13447_1645000677"></a>

## Operational templates

These templates complete the operational interfaces without duplicating the full runbooks in sections 53, 55–57. Their fields are minimum record content, not an instruction to bypass the adopting organization’s incident/change system.

### Architecture decision record


<a id="source-table-1549"></a>

| Record area | Required fields / action |
| --- | --- |
| Identity | ADR ID, title, status, owner, date, superseded decisions |
| Context | Problem, threat/failure assumptions, affected scope, requirements and sources |
| Alternatives | Viable options, interoperability/portability implications and explicit rejection rationale |
| Decision | Chosen design, boundary/authority model, dependencies, approved conditions |
| Consequences | Security and operational risks, capacity/cost, qualification tests, migration/exit, review trigger |

### Partial-apply recovery record


<a id="source-table-1551"></a>

| Record area | Required fields / action |
| --- | --- |
| Detect | Operation ID, target generation, stage/completion tokens, state locks and latest confirmed provider outcome |
| Stabilize | Prove active writer status, restrict new actions, preserve data and evidence |
| Reconcile | Query owned resources, IPAM/DNS/reservations, effective policy and readiness; resolve unknown outcomes |
| Decide | Authorized converge/compensate/manual intervention; expected data impact and approval |
| Close | Run changed-path tests, bind new evidence, release reservations/locks safely and record root cause |

### Key or identity dependency outage record


<a id="source-table-1553"></a>

| Record area | Required fields / action |
| --- | --- |
| Scope | Affected key/identity service, tenants, new versus existing sessions/data access |
| Continuity | Qualified cache/session behavior; no plaintext or unrestricted local-account fallback |
| Recover | Approved break-glass, protected recovery material, target-service health and audit |
| Revoke/reconcile | Rotate or revoke compromised/recovery credentials, reassess grants and retained copies |
| Accept | Actual application/service validation, security owner approval and incident closure |

### Retention and sanitization record


<a id="source-table-1555"></a>

| Record area | Required fields / action |
| --- | --- |
| Data lineage | Original WSD, copy/replica/snapshot IDs, class, owners and storage locations |
| Obligations | Retention policy, holds, disposition authority, key dependencies and review dates |
| Action | Approved method, media/key scope, execution authority/time and affected copies |
| Verification | Technical sanitization evidence or explicit retained exceptions; no fabricated total-destruction assertion |
| Closure | Tombstone, remaining obligations, evidence retention and final access revocation |

Change/exception approvals, ZIP endpoint-authority approvals, platform qualification and operational handover records use the same identity/version/evidence conventions. Their signed decisions are stored in the approved system of record; a string labelled approvalRef is not proof that approval actually exists.

[Previous chapter](75-appendix-f-proposed-local-engineering-parameters.md) · [Chapter index](README.md) · [Next chapter](77-appendix-h-primary-sources-and-implementation-references.md)
