# Completion publication — verified merged snapshot

**Review date:** 18 September 2026  
**Tested main commit:** `b184bc629b996e1cd658c389ba707a99f89f7c07`  
**Tested tree:** `54df3ddd7924038ad6c877249b2579ada55a59cd`  
**Result:** repository/documentation checks and the separate Terraform and Ansible jobs passed for this exact merged snapshot.

[Observed post-merge run](https://github.com/awalker0878/multi-tenant/actions/runs/35300272211) · [Machine-readable observation](../../evidence/completion-publication/verification.json) · [Corrective dispositions](completion-corrections.md)

## Reconcile publication with the repository, not the older conversation

The previous continuation stopped at `audit/complete-docs-and-validation` and described the document migration as unpublished. The repository subsequently advanced through the integrated correction and PR #11. The current check therefore examined the merged b184bc6 snapshot and its post-merge run instead of replaying that older branch over newer work.

The remaining publication discrepancy was CA-11: its source record still said the final engine run was pending. That hold is now resolved for the named snapshot by the actual successful post-merge run. CA-01 through CA-10 are not silently reassigned, and none of the organizational or native-evidence holds is converted to acceptance.

## Observed checks

| Check | Result for b184bc6 | Scope |
|---|---|---|
| Current Git integrity | 1,100 tracked files matched HEAD | Byte consistency, not signer or approval authenticity |
| Word-to-Markdown and governance checks | 36,281 passed; zero failures | 28 source documents, 486 tables, 7,976 independently compared table cells and 13 code paragraphs |
| Local links | 10,719 checked, including 3,726 fragment links | Local targets only; external references were not revalidated |
| Full unit and source suite | 556 passed; no failures, errors or skips | Includes local protocol fixtures, not native vendor qualification |
| Offline routing model | 80 passed | Modeled routing/permission outcomes, not packet or native evidence |
| Terraform | Engine 1.13.5; verifier passed | Ten modules and ten roots; backend-disabled root validation, module schemas and mocked plan-only tests |
| Provider locks | 20 committed files passed selection review | Real package/schema verification occurs in the separate engine step |
| Ansible | Core 2.19.7; all 11 checks passed | Local staging, zero-change repeat, check-mode non-mutation and negative inputs; no native contact |

The 36 source-derived ADRs are part of the 38-record register; the two legacy decision aliases are navigation, not additional decisions. The six maintained design records and 540 assertion-allocation rows remain proposed records for accountable review. Test specifications CT, RA, W14 and Q11 overlap and remain separate from these executed publishing and toolchain results.

The exact workflow, job IDs and producer-reported artifact digests are recorded in the JSON observation. This review read authenticated GitHub metadata and decoded job logs. It did not independently download or hash the binary artifact contents. The 14-day CI artifact retention is not permanent archival custody; preserve required evidence through the existing controlled process before expiry.

## What is on main

The merged correction includes preserved code-block structure, ordered-table and ADR semantic checks, current-checkout integrity, a working Proposed/Accepted/Rejected/Superseded ADR record model, a separate maintained-design workspace, individual historical-audit dispositions, all four verification families, explicit implementation obligations and reviewed provider locks. The subsequent integration fix establishes one canonical record model and retains the earlier regression intentions rather than skipping failures.

[Integration audit and canonical paths](main-integration-audit.md) · [Maintained RAD/TAD and solution records](../current/README.md) · [ADR register](../adr/README.md) · [Implementation allocation](../implementation/assertion-allocation.md) · [Verification-family selection](verification-families.md)

## Boundaries that remain open

CA-06 still requires owner review of the missing-original/replacement-document scope. The standalone earlier RAD/TAD files are not represented as recovered originals. CA-07 keeps F01–F24 open for the responsible reviewers; retaining a disposition is not issuing closure. CA-09 requires actual engineering adoption and native evidence for the selected service and platform combination.

All actual architectural ADRs remain Proposed. No site values, firewall choice, physical co-residency acceptance, issued operating authority, native isolation test or measured recovery result is invented. Source and toolchain validation does not close EC/SE attachments, native policy/HA, authoritative service integrations or production activation.

## How this evidence ages

This is a pinned observation of b184bc6, not an evergreen declaration that the repository's newest commit passed. The commit publishing this record and every later change require their own successful pull-request checks and post-merge validation. Their actual run links belong in the change discussion; do not rewrite this observation to claim it tested a different revision.

[Documentation home](../README.md) · [Testing procedure](../TESTING.md)
