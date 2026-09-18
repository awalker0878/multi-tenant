# Appendix J — Audit closure, migration and release checks

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:1685 BEGIN -->

<a id="__RefHeading___Toc13453_1645000677"></a>
<a id="app_J"></a>

<!-- SOURCE-BLOCK HB11:1685 END -->

<!-- SOURCE-BLOCK HB11:1686 BEGIN -->

<a id="__RefHeading___Toc13455_1645000677"></a>

## Audit and migration registers

<!-- SOURCE-BLOCK HB11:1686 END -->

<!-- SOURCE-BLOCK HB11:1687 BEGIN -->

The following register shows how the audit was resolved in the document and contract package. “Addressed” means the requirement/model/procedure is now specified and cross-referenced; it does not mean a real platform has executed the test or received approval. Additional source verification corrected the 2026 control/cryptography baseline and refined several earlier audit recommendations.

<!-- SOURCE-BLOCK HB11:1687 END -->

<!-- SOURCE-BLOCK HB11:1688 BEGIN -->

A01 — REZ/internal zone model

<!-- SOURCE-BLOCK HB11:1688 END -->

<!-- SOURCE-BLOCK HB11:1689 BEGIN -->

Removed REZ from internal zone enums. Introduced ExternalDomain and explicit REZ\_PARTNER semantics; MZ provider-controlled.

<!-- SOURCE-BLOCK HB11:1689 END -->

<!-- SOURCE-BLOCK HB11:1690 BEGIN -->

Location: 10; Appendix A  \|  Addressed in document/contracts

<!-- SOURCE-BLOCK HB11:1690 END -->

<!-- SOURCE-BLOCK HB11:1691 BEGIN -->

A02 — Cloud zoning standard omitted

<!-- SOURCE-BLOCK HB11:1691 END -->

<!-- SOURCE-BLOCK HB11:1692 BEGIN -->

Added ITSP.80.023 and qualified logical/distributed ZIP semantics; no appliance-only restriction.

<!-- SOURCE-BLOCK HB11:1692 END -->

<!-- SOURCE-BLOCK HB11:1693 BEGIN -->

Location: 3, 10–12, 34  \|  Addressed in source baseline

<!-- SOURCE-BLOCK HB11:1693 END -->

<!-- SOURCE-BLOCK HB11:1694 BEGIN -->

A03 — MZ/OOB conflation

<!-- SOURCE-BLOCK HB11:1694 END -->

<!-- SOURCE-BLOCK HB11:1695 BEGIN -->

Separated management-zone security semantics, OOB transport, privileged access and provider control APIs.

<!-- SOURCE-BLOCK HB11:1695 END -->

<!-- SOURCE-BLOCK HB11:1696 BEGIN -->

Location: 6, 12  \|  Addressed in model

<!-- SOURCE-BLOCK HB11:1696 END -->

<!-- SOURCE-BLOCK HB11:1697 BEGIN -->

A04 — ZIP governance incomplete

<!-- SOURCE-BLOCK HB11:1697 END -->

<!-- SOURCE-BLOCK HB11:1698 BEGIN -->

Two endpoints, joint authority, deny default, management path, sensors/posture, symmetry and qualification specified.

<!-- SOURCE-BLOCK HB11:1698 END -->

<!-- SOURCE-BLOCK HB11:1699 BEGIN -->

Location: 11, 20, 52  \|  Addressed; live qualification required

<!-- SOURCE-BLOCK HB11:1699 END -->

<!-- SOURCE-BLOCK HB11:1700 BEGIN -->

A05 — Physical co-residency undefined

<!-- SOURCE-BLOCK HB11:1700 END -->

<!-- SOURCE-BLOCK HB11:1701 BEGIN -->

Zone-specific host-pool baseline and explicit dedication vector; exceptions require evidence and risk decision.

<!-- SOURCE-BLOCK HB11:1701 END -->

<!-- SOURCE-BLOCK HB11:1702 BEGIN -->

Location: 22, 47  \|  Addressed; deployment profile required

<!-- SOURCE-BLOCK HB11:1702 END -->

<!-- SOURCE-BLOCK HB11:1703 BEGIN -->

A06 — Ambiguous categorization

<!-- SOURCE-BLOCK HB11:1703 END -->

<!-- SOURCE-BLOCK HB11:1704 BEGIN -->

Separated confidentiality, integrity, availability impact, uptime SLO and recovery objectives.

<!-- SOURCE-BLOCK HB11:1704 END -->

<!-- SOURCE-BLOCK HB11:1705 BEGIN -->

Location: 4, 28; Appendix A  \|  Addressed in model/contracts

<!-- SOURCE-BLOCK HB11:1705 END -->

<!-- SOURCE-BLOCK HB11:1706 BEGIN -->

A07 — Incomplete requirement index

<!-- SOURCE-BLOCK HB11:1706 END -->

<!-- SOURCE-BLOCK HB11:1707 BEGIN -->

All original 99 IDs retained or explicitly revised; generated full active catalogue plus verification/source links.

<!-- SOURCE-BLOCK HB11:1707 END -->

<!-- SOURCE-BLOCK HB11:1708 BEGIN -->

Location: Appendix C; requirements.json  \|  Addressed and mechanically checked

<!-- SOURCE-BLOCK HB11:1708 END -->

<!-- SOURCE-BLOCK HB11:1709 BEGIN -->

A08 — Network-heavy scope

<!-- SOURCE-BLOCK HB11:1709 END -->

<!-- SOURCE-BLOCK HB11:1710 BEGIN -->

Added compute, storage, IAM, cryptography, images, protection, availability, location and shared application responsibility.

<!-- SOURCE-BLOCK HB11:1710 END -->

<!-- SOURCE-BLOCK HB11:1711 BEGIN -->

Location: 22–31  \|  Addressed in chapters and requirements

<!-- SOURCE-BLOCK HB11:1711 END -->

<!-- SOURCE-BLOCK HB11:1712 BEGIN -->

A09 — WSD not production-grade contract

<!-- SOURCE-BLOCK HB11:1712 END -->

<!-- SOURCE-BLOCK HB11:1713 BEGIN -->

Closed typed object schemas, metadata generation/status split, desired-state references and lifecycle semantics.

<!-- SOURCE-BLOCK HB11:1713 END -->

<!-- SOURCE-BLOCK HB11:1714 BEGIN -->

Location: 39–41; Appendix A  \|  Addressed as reference contracts; controller implementation external

<!-- SOURCE-BLOCK HB11:1714 END -->

<!-- SOURCE-BLOCK HB11:1715 BEGIN -->

A10 — Thin Flow Intent

<!-- SOURCE-BLOCK HB11:1715 END -->

<!-- SOURCE-BLOCK HB11:1716 BEGIN -->

Typed endpoints/service profiles, validity, state/TLS/logging, policy precedence and graph admission.

<!-- SOURCE-BLOCK HB11:1716 END -->

<!-- SOURCE-BLOCK HB11:1717 BEGIN -->

Location: 19, 40; Appendix A  \|  Addressed in model/contracts

<!-- SOURCE-BLOCK HB11:1717 END -->

<!-- SOURCE-BLOCK HB11:1718 BEGIN -->

A11 — Thin fabric engineering

<!-- SOURCE-BLOCK HB11:1718 END -->

<!-- SOURCE-BLOCK HB11:1719 BEGIN -->

Underlay, EVPN, MTU, route authority, multihoming, filtering, scale, maintenance and failure qualification.

<!-- SOURCE-BLOCK HB11:1719 END -->

<!-- SOURCE-BLOCK HB11:1720 BEGIN -->

Location: 32–33  \|  Addressed; vendor/site realization required

<!-- SOURCE-BLOCK HB11:1720 END -->

<!-- SOURCE-BLOCK HB11:1721 BEGIN -->

A12 — No common attachment contract

<!-- SOURCE-BLOCK HB11:1721 END -->

<!-- SOURCE-BLOCK HB11:1722 BEGIN -->

Added provider-internal EdgeAttachment and tested shared-attachment isolation.

<!-- SOURCE-BLOCK HB11:1722 END -->

<!-- SOURCE-BLOCK HB11:1723 BEGIN -->

Location: 20, 32–38; Appendix A  \|  Addressed in model/contracts

<!-- SOURCE-BLOCK HB11:1723 END -->

<!-- SOURCE-BLOCK HB11:1724 BEGIN -->

A13 — Terraform gaps

<!-- SOURCE-BLOCK HB11:1724 END -->

<!-- SOURCE-BLOCK HB11:1725 BEGIN -->

Provider versus module locking, immutable plans, write-only/ephemeral support, state recovery and staged compensation.

<!-- SOURCE-BLOCK HB11:1725 END -->

<!-- SOURCE-BLOCK HB11:1726 BEGIN -->

Location: 42–45; Appendix B  \|  Addressed in engineering requirements

<!-- SOURCE-BLOCK HB11:1726 END -->

<!-- SOURCE-BLOCK HB11:1727 BEGIN -->

A14 — Unversioned platform capability claims

<!-- SOURCE-BLOCK HB11:1727 END -->

<!-- SOURCE-BLOCK HB11:1728 BEGIN -->

Exact tuple, Candidate/Qualified/Suspended lifecycle, evidence, review expiry and verified limits; no invented qualification.

<!-- SOURCE-BLOCK HB11:1728 END -->

<!-- SOURCE-BLOCK HB11:1729 BEGIN -->

Location: 34–38; Appendix A  \|  Addressed; examples intentionally Candidate

<!-- SOURCE-BLOCK HB11:1729 END -->

<!-- SOURCE-BLOCK HB11:1730 BEGIN -->

A15 — Assurance labels not measurable

<!-- SOURCE-BLOCK HB11:1730 END -->

<!-- SOURCE-BLOCK HB11:1731 BEGIN -->

Explicit per-layer isolation, approved parameters, test/freshness and exception rules.

<!-- SOURCE-BLOCK HB11:1731 END -->

<!-- SOURCE-BLOCK HB11:1732 BEGIN -->

Location: 47; Appendix F  \|  Addressed; example values are proposed

<!-- SOURCE-BLOCK HB11:1732 END -->

<!-- SOURCE-BLOCK HB11:1733 BEGIN -->

A16 — Small test catalogue

<!-- SOURCE-BLOCK HB11:1733 END -->

<!-- SOURCE-BLOCK HB11:1734 BEGIN -->

Expanded to 80 detailed positive/negative/failure/recovery/lifecycle procedures with all results not-run.

<!-- SOURCE-BLOCK HB11:1734 END -->

<!-- SOURCE-BLOCK HB11:1735 BEGIN -->

Location: 48; Appendix D  \|  Specification complete; live tests not executed

<!-- SOURCE-BLOCK HB11:1735 END -->

<!-- SOURCE-BLOCK HB11:1736 BEGIN -->

A17 — Evidence/control linkage weak

<!-- SOURCE-BLOCK HB11:1736 END -->

<!-- SOURCE-BLOCK HB11:1737 BEGIN -->

Requirement → source edition/family → object → test → artifact → decision; authorization separate.

<!-- SOURCE-BLOCK HB11:1737 END -->

<!-- SOURCE-BLOCK HB11:1738 BEGIN -->

Location: 49; Appendix E  \|  Addressed; final selected controls need assessor tailoring

<!-- SOURCE-BLOCK HB11:1738 END -->

<!-- SOURCE-BLOCK HB11:1739 BEGIN -->

A18 — Logging/IR underdeveloped

<!-- SOURCE-BLOCK HB11:1739 END -->

<!-- SOURCE-BLOCK HB11:1740 BEGIN -->

Current logging/event process references, event schema, buffering/time/privacy and scoped incident overrides.

<!-- SOURCE-BLOCK HB11:1740 END -->

<!-- SOURCE-BLOCK HB11:1741 BEGIN -->

Location: 50, 55  \|  Addressed

<!-- SOURCE-BLOCK HB11:1741 END -->

<!-- SOURCE-BLOCK HB11:1742 BEGIN -->

A19 — Backup/retention/disposal thin

<!-- SOURCE-BLOCK HB11:1742 END -->

<!-- SOURCE-BLOCK HB11:1743 BEGIN -->

Protected administration, immutable copy policy, isolated restore, lineage/holds/key lifetime and sanitization evidence.

<!-- SOURCE-BLOCK HB11:1743 END -->

<!-- SOURCE-BLOCK HB11:1744 BEGIN -->

Location: 23, 25, 27, 53, 56  \|  Addressed

<!-- SOURCE-BLOCK HB11:1744 END -->

<!-- SOURCE-BLOCK HB11:1745 BEGIN -->

A20 — Offboarding numbering and dependency order

<!-- SOURCE-BLOCK HB11:1745 END -->

<!-- SOURCE-BLOCK HB11:1746 BEGIN -->

Independent steps 1–9; retention protected before paths/keys revoked; tombstones and shared dependencies preserved.

<!-- SOURCE-BLOCK HB11:1746 END -->

<!-- SOURCE-BLOCK HB11:1747 BEGIN -->

Location: 56  \|  Addressed

<!-- SOURCE-BLOCK HB11:1747 END -->

<!-- SOURCE-BLOCK HB11:1748 BEGIN -->

A21 — SLO/RTO/RPO/capacity undefined

<!-- SOURCE-BLOCK HB11:1748 END -->

<!-- SOURCE-BLOCK HB11:1749 BEGIN -->

Separate service profiles, measurement boundaries, failed-capacity admission and procurement/consumption accounting.

<!-- SOURCE-BLOCK HB11:1749 END -->

<!-- SOURCE-BLOCK HB11:1750 BEGIN -->

Location: 28, 30, 51–53  \|  Addressed; targets require local adoption

<!-- SOURCE-BLOCK HB11:1750 END -->

<!-- SOURCE-BLOCK HB11:1751 BEGIN -->

A22 — Word navigation and publishing

<!-- SOURCE-BLOCK HB11:1751 END -->

<!-- SOURCE-BLOCK HB11:1752 BEGIN -->

Real TOC, Word headings, bookmarks, numbered figures/cross-references, descriptive source links/alt text and rendered review.

<!-- SOURCE-BLOCK HB11:1752 END -->

<!-- SOURCE-BLOCK HB11:1753 BEGIN -->

Location: Whole document  \|  Checked during release build

<!-- SOURCE-BLOCK HB11:1753 END -->

<!-- SOURCE-BLOCK HB11:1754 BEGIN -->

A23 — 2026 control-catalogue transition

<!-- SOURCE-BLOCK HB11:1754 END -->

<!-- SOURCE-BLOCK HB11:1755 BEGIN -->

Added ITSP.10.033 effective 31 March 2026; supersedes Annex 3A only; source edition and numbering migration recorded.

<!-- SOURCE-BLOCK HB11:1755 END -->

<!-- SOURCE-BLOCK HB11:1756 BEGIN -->

Location: 3; Appendix E  \|  Additional researched correction

<!-- SOURCE-BLOCK HB11:1756 END -->

<!-- SOURCE-BLOCK HB11:1757 BEGIN -->

A24 — 2026 cryptographic baseline

<!-- SOURCE-BLOCK HB11:1757 END -->

<!-- SOURCE-BLOCK HB11:1758 BEGIN -->

Added ITSP.40.111 v5 effective 29 May 2026 and versioned crypto policy rather than permanent legacy algorithm assumptions.

<!-- SOURCE-BLOCK HB11:1758 END -->

<!-- SOURCE-BLOCK HB11:1759 BEGIN -->

Location: 3, 25  \|  Additional researched correction

<!-- SOURCE-BLOCK HB11:1759 END -->

<!-- SOURCE-BLOCK HB11:1760 BEGIN -->

A25 — Overstatement of completion/certification

<!-- SOURCE-BLOCK HB11:1760 END -->

<!-- SOURCE-BLOCK HB11:1761 BEGIN -->

Separated document/contract validation from platform test execution, technical readiness and formal authorization.

<!-- SOURCE-BLOCK HB11:1761 END -->

<!-- SOURCE-BLOCK HB11:1762 BEGIN -->

Location: 1, 48–49, 61–62  \|  Addressed throughout

<!-- SOURCE-BLOCK HB11:1762 END -->

<!-- SOURCE-BLOCK HB11:1763 BEGIN -->

### Original section migration

<!-- SOURCE-BLOCK HB11:1763 END -->

<!-- SOURCE-BLOCK HB11:1764 BEGIN -->


<a id="source-table-1764"></a>

| v1.0 section | v1.1 primary location | v1.0 section | v1.1 primary location |
| --- | --- | --- | --- |
| 1 | §1 | 27 | §34 |
| 2 | §2 | 28 | §39 |
| 3 | §3 | 29 | §41 |
| 4 | §6 | 30 | §42 |
| 5 | §5 | 31 | §43 |
| 6 | §6 | 32 | §40 |
| 7 | §7 | 33 | §45 |
| 8 | §8 | 34 | §44 |
| 9 | §9 | 35 | §46 |
| 10 | §10 | 36 | §47 |
| 11 | §11 | 37 | §48 |
| 12 | §12 | 38 | §49 |
| 13 | §32 | 39 | §50 |
| 14 | §13 | 40 | §51 |
| 15 | §14 | 41 | §52 |
| 16 | §15 | 42 | §27 |
| 17 | §16 | 43 | §55 |
| 18 | §17 | 44 | §59 |
| 19 | §18 | 45 | §56 |
| 20 | §19 | 46 | §57 |
| 21 | §21 | 47 | §58 |
| 22 | §34 | 48 | §60 |
| 23 | §35 | 49 | §60 |
| 24 | §36 | 50 | §61 |
| 25 | §37 | 51 | §61 |
| 26 | §38 | 52 | §62 |

<!-- SOURCE-BLOCK HB11:1764 END -->

<!-- SOURCE-BLOCK HB11:1765 BEGIN -->

Every original requirement ID and its exact old/new wording is included in catalogues/v1\_0\_requirement\_migration.json. The section map identifies the primary home; new cross-cutting requirements may also appear in related chapters. Original appendices were redistributed into the complete contract, requirement, test, traceability and reference appendices here.

<!-- SOURCE-BLOCK HB11:1765 END -->

<!-- SOURCE-BLOCK HB11:1766 BEGIN -->

### Offline release validation

<!-- SOURCE-BLOCK HB11:1766 END -->

<!-- SOURCE-BLOCK HB11:1767 BEGIN -->


<a id="source-table-1767"></a>

| Check class | Result for this package |
| --- | --- |
| Chapter and original-source coverage | 62 chapters; all 52 original sections mapped; all 99 original requirement IDs retained/revised |
| Normative and verification catalogue | 194 active requirements; all test/source links resolve; all 80 tests have requirement links |
| Contract coverage | 33 typed kinds; 43 consistent example objects; consumer request without server-owned status |
| Offline validation suite | 50 checks passed; 0 failed; includes structural/semantic rejection fixtures |
| Infrastructure test execution | 80 procedures specified; all marked not-run; no target platform contacted or certified |
| Implementation readiness | Reference profiles remain Proposed/Candidate; authorization NotIssued; readiness deliberately blocked |

<!-- SOURCE-BLOCK HB11:1767 END -->

<!-- SOURCE-BLOCK HB11:1768 BEGIN -->

Publishing checks are performed against the actual generated DOCX/PDF: populated TOC, headings and numbered chapters; valid bookmarks, SEQ/REF fields and source links; complete requirement/test text; meaningful figure descriptions; table pagination and page-image review. Machine validation proves package consistency, not completeness of every possible future threat or production security assurance.

<!-- SOURCE-BLOCK HB11:1768 END -->

<!-- SOURCE-BLOCK HB11:1769 BEGIN -->

End-state architecture

<!-- SOURCE-BLOCK HB11:1769 END -->

<!-- SOURCE-BLOCK HB11:1770 BEGIN -->

Standardize the security, service, lifecycle and evidence semantics. Keep platform realizations replaceable, trust transitions explicit and management authority separate. Admit only what the qualified platform can preserve, prove recovery as well as provisioning, and never confuse a successful automation run with an authorized service. \[[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)\]

<!-- SOURCE-BLOCK HB11:1770 END -->

[Previous chapter](78-appendix-i-glossary.md) · [Chapter index](README.md)
