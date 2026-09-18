# Independent audit of the v1.1 handbook and contract package

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.

## Chapters

- [Executive determination](01-executive-determination.md)
- [Scope, method and confirmed improvements](02-scope-method-and-confirmed-improvements.md)
- [F01  |  Reference identity does not preserve tenant namespace](03-f01-reference-identity-does-not-preserve-tenant-namespace.md)
- [F02  |  Cross-object consistency checks do not cover the complete graph](04-f02-cross-object-consistency-checks-do-not-cover-the-complete-graph.md)
- [F03  |  IPv6-only is offered but cannot be represented end to end](05-f03-ipv6-only-is-offered-but-cannot-be-represented-end-to-end.md)
- [F04  |  Reference DNS service is UDP-only](06-f04-reference-dns-service-is-udp-only.md)
- [F05  |  FlowProfile protocol semantics remain incomplete](07-f05-flowprofile-protocol-semantics-remain-incomplete.md)
- [F06  |  Security-sensitive profile approval is not a consistent contract](08-f06-security-sensitive-profile-approval-is-not-a-consistent-contract.md)
- [F07  |  Qualification lifecycle differs between prose and schema](09-f07-qualification-lifecycle-differs-between-prose-and-schema.md)
- [F08  |  Qualification record cannot fully express QUAL-001](10-f08-qualification-record-cannot-fully-express-qual-001.md)
- [F09  |  Evidence validation accepts incomplete readiness assertions](11-f09-evidence-validation-accepts-incomplete-readiness-assertions.md)
- [F10  |  Per-control evidence trace is described but not contracted](12-f10-per-control-evidence-trace-is-described-but-not-contracted.md)
- [F11  |  PlacementProfile does not express required location distinctions](13-f11-placementprofile-does-not-express-required-location-distinctions.md)
- [F12  |  API lifecycle is not closed over the required object graph](14-f12-api-lifecycle-is-not-closed-over-the-required-object-graph.md)
- [F13  |  Breaking-change policy and API version naming disagree](15-f13-breaking-change-policy-and-api-version-naming-disagree.md)
- [F14  |  Reference validation needs explicit coverage tiers and stronger negatives](16-f14-reference-validation-needs-explicit-coverage-tiers-and-stronger-negatives.md)
- [F15  |  Printed control-family crosswalk omits existing catalogue mappings](17-f15-printed-control-family-crosswalk-omits-existing-catalogue-mappings.md)
- [F16  |  Requirement-to-test links do not yet prove assertion-level coverage](18-f16-requirement-to-test-links-do-not-yet-prove-assertion-level-coverage.md)
- [F17  |  Qualification and portability need separate test applicability rules](19-f17-qualification-and-portability-need-separate-test-applicability-rules.md)
- [F18  |  Cadence and execution-status records need reconciliation](20-f18-cadence-and-execution-status-records-need-reconciliation.md)
- [F19  |  Document fencing and pre/post-activation verification explicitly](21-f19-document-fencing-and-pre-post-activation-verification-explicitly.md)
- [F20  |  Add one end-to-end service materialization contract](22-f20-add-one-end-to-end-service-materialization-contract.md)
- [F21  |  Complete protocol-profile and standards-adoption traceability](23-f21-complete-protocol-profile-and-standards-adoption-traceability.md)
- [F22  |  Make the release build and source evidence reproducible](24-f22-make-the-release-build-and-source-evidence-reproducible.md)
- [F23  |  Improve reader navigation and verification evidence, not page count](25-f23-improve-reader-navigation-and-verification-evidence-not-page-count.md)
- [F24  |  Define completion independently for each delivered layer](26-f24-define-completion-independently-for-each-delivered-layer.md)
- [Evidence inventory and external checks](27-evidence-inventory-and-external-checks.md)

## Source front matter
<!-- SOURCE-BLOCK AUD11:0 BEGIN -->

*Independent audit*

<!-- SOURCE-BLOCK AUD11:0 END -->

<!-- SOURCE-BLOCK AUD11:1 BEGIN -->

## Portable Multi-Tenant<br>Secure Hosting

<!-- SOURCE-BLOCK AUD11:1 END -->

<!-- SOURCE-BLOCK AUD11:2 BEGIN -->

*Handbook v1.1 and companion package<br>Architecture, contract consistency and completeness*

<!-- SOURCE-BLOCK AUD11:2 END -->
