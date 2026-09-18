# 6. Release the architecture as an accountable engineering contract

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Service_Design_and_Decision_Development.docx) · [Chapter index](README.md)

> **Source:** SDP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 133c2512e904737c1f410106fd1b421fba8309965af0621785b250402fb9214e -->
<a id="SDP_06"></a>

The HLD remains the project design record. Use this completion record to attach the developed decisions to that record, rather than creating another conflicting source of truth.

Design basis and related records: [AK §8](../../architecture/delivery-guide/8-engineering-handoff-and-change-impact.md#AK_08)  •  [AT §10](../../templates/hld/10-architecture-review-and-engineering-handoff.md#AT_10)  •  [DEL §2](../../governance/delivery-framework/2-preserve-stable-deliverables-and-explicit-handoffs.md#DEL_02)


<a id="source-table-69"></a>

| Decision / response | What the architect hands over | Working reference |
| --- | --- | --- |
| Offered scope | Service boundary, excluded extensions, categorization and actual responsibility split. | \[Enter sdp service scope\] |
| Approved sharing | Per-layer dedicated/shared disposition, exceptions and eligible recovery placement. | \[Enter sdp sharing decision\] |
| Boundary realization | Selected option, rejected alternatives and required forward/reply enforcement. | \[Enter sdp boundary decision\] |
| Required dependencies | Producer acceptance, client scope, recovery and location constraints. | \[Enter sdp dependencies\] |
| Acceptance allocation | Assertions, qualification stage, evidence owner and appropriate decision authority. | \[Enter sdp acceptance allocation\] |
| Open decisions | Named owner, blocking gate, due/review trigger and evidence needed to close. | \[Enter sdp open decisions\] |

At the walkthrough, trace one approved application path, one denied cross-tenant path, one virtual-disk attachment, one privileged management action and one recovery dependency. Use consistent identities across views and schedules. Differences become tracked dispositions, not explanatory comments lost inside a drawing.

A changed address normally belongs to detailed engineering. Changed zone sharing, inspection obligations, administrative authority, recovery promise or external exposure can change the architecture. The architecture owner determines which records and deployed services must be re-evaluated.

Actual status for this release: developed reference method supplied; project scope, approving authorities and engineering acceptance remain unassigned.

Continue with: [NBD §6](../../engineering/network-boundaries/6-issue-an-interface-control-and-handoff-record.md#NBD_06)  •  [PBS §9](../../engineering/platform-build/9-release-a-native-build-package-that-can-be-independently-reviewed.md#PBS_09)

[Previous chapter](5-make-capacity-on-demand-and-exit-economically-explainable.md) · [Chapter index](README.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0003 — Let the infrastructure architecture lead the tooling](../../adr/0003-let-the-infrastructure-architecture-lead-the-tooling.md)
- [ADR-0034 — Classify change by architectural impact rather than file location](../../adr/0034-classify-change-by-architectural-impact-rather-than-file-location.md)

<!-- END GENERATED DECISION LINKS -->
