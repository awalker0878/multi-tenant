# Main integration audit and follow-up

**Audited commit:** `5230619fa3e4dbb997166aaeb76473d87a8ed880`<br>
**Audited tree:** `9c41b01e5b1ef0f7bc1af16b6c19025744c8dedf`<br>
**Scope:** exact merged repository, its documentation-authority integration, local regression failures and CI boundaries. This is not native service qualification or a new architecture approval.

## Observed state, not a replay of a previous ZIP claim

The current main tree contained both earlier correction variants: the active frozen-transcription plus `docs/current` model and leftovers from the source-block-amendment model. A local reconstruction matched the authenticated GitHub tree byte for byte before any edit. Local tests reproduced the same six failures and three errors observed in [main run 35297280301](https://github.com/awalker0878/multi-tenant/actions/runs/35297280301).

That main run **passed the actual Terraform and Ansible jobs**. Its repository job passed integrity, static documentation checks and the independent code/table comparisons, but failed the aggregate regression suite: 527 tests, six failures, three errors, no skips. All nine failing cases came from `test_completion_remediation.py`, which still read obsolete fields and source-block delimiters. The corresponding retained tests in `test_completion_corrections.py` exercised the newer model successfully. A passing standalone documentation check therefore did not mean the repository integration was consistent.

## Findings and targeted correction

| Finding | Observed problem | Treatment in this change |
|---|---|---|
| MI-01 — Two live record models | Older tests/renderer expected `evidence`, an accepting authority alias, reciprocal lists and source-block wrappers that no longer described the merged sources. | Keep one canonical ADR format and independent source checker. Migrate all 21 older regression intentions to it, retaining semantic negatives and command-boundary assertions. No test is skipped to make main green. |
| MI-02 — Duplicate decision publications | ADR-0037 and ADR-0038 each had two differently named proposed pages; only one per ID was checked against the registry. | Preserve old URLs as explicit navigation aliases without a second decision/status. A new gate detects unregistered duplicate numbered ADR pages. No lifecycle acceptance or supersession is invented. |
| MI-03 — Competing assurance/authoring tools | An earlier 370-row allocation and builder coexisted with the maintained 540-row record. The old builder expected a different verification-family format. | Mark the earlier views as historical, identify one canonical record per responsibility, delegate the old build command to the maintained builder, and make the retired amendment writer stop before any write. Historical input/evidence and the complete earlier generated Markdown remain byte-identical; old view URLs become explicit historical navigation. |
| MI-04 — Proposed records could imply a decision | The active ADR validator required evidence for Accepted but did not reject populated acceptance fields on Proposed records. | Require typed, exact governance fields; Proposed cannot carry a completed lifecycle decision. Reject obsolete aliases, duplicate evidence, malformed successors and cycles. No actual record changes status. |
| MI-05 — Maintained metadata could disagree with its page | A maintained design page could display Accepted or a different owner/version while its metadata still said Proposed. | Reconcile the displayed version/status/owner and latest history version with the maintained record. Ordinary design prose remains editable without altering frozen originals. |
| MI-06 — Test-family mappings checked counts, not original associations | A valid but wrong CT reference could retain all family IDs/counts and pass. | Compare the complete generated supplemental mappings with the original RA/Q11/W14 records, including applicability, order and not-run state. Keep the four families non-additive specifications. |
| MI-07 — Restore dependency-review gate after actual locks arrived | The older missing-lock blocker had been removed from CI; real lockfiles are now committed. | Run the existing real-lock selection review before the already backend-disabled engine job. Missing locks fail explicitly; no hashes or provider selections are fabricated. |

The single source-format decision is a reconciliation of what main already adopted, not a new application architecture. Native Terraform modules, roots, Ansible roles, observers, DNS implementation, original reference documents and retained published evidence are outside the changed semantic scope.

## Canonical working paths

| Responsibility | Maintained record or tool |
|---|---|
| Source transcriptions and code/table fidelity | `sources/documentation/conversion_manifest.json`, `scripts/documentation_structure.py` |
| Editable RAD/TAD/solution/interface/transition records | `docs/current/`, `sources/documentation/current_design_records.json` |
| ADR source, lifecycle and deterministic pages | `sources/documentation/adr_records.json`, `scripts/adr_lifecycle.py` |
| Individual implementation obligations | [540-row allocation](../implementation/assertion-allocation.md) and `sources/assurance/implementation_assertions.json` |
| Native realization and procedure selection | [Verification-family index](verification-families.md) and original CT/RA/W14/Q11 sources |
| Historical audit applicability and remaining proof | [Maintained disposition view](historical-dispositions.md); original F01–F24 findings remain unclosed |
| Prior conflicting paths | [Integration authority map](../../sources/documentation/integration_authority.json), explicit historical notices and decision URL aliases |

`documentation_controls.py` retains only named delegations to the active ADR renderer/validator. It does not accept an older governance dialect or provide a second writer. `record_doc_amendment.py` returns a nonzero retired-model result for every invocation, including its former write flag. Keep source transcriptions immutable; use the maintained records for actual proposed design edits.

## Verification and release conditions

Run `python scripts/check_documentation.py` and `python tools/check_local.py`. The former includes the integration authority gate, displayed metadata, independent source structure and original procedure associations. The latter preserves the older regression coverage and adds malformed-input and cross-model negative tests. `python scripts/check_dependency_locks.py` checks actual committed selections before the separate Terraform engine step; the real engine still verifies package/schema/mock semantics.

The pull request's **exact final revision** must pass repository, Terraform and Ansible jobs before merge. Prior success from the audited baseline is not used to bypass that condition. Local synthetic CLI responses remain unit tests, not engine evidence. No PR job uses native credentials, applies infrastructure or writes this repository. Consult the PR/run records for final publication status instead of inferring it from this source page.

## Next architecture/engineering milestone

Continue the first bounded native reference service only after its site and supported platform/security-edge combination are selected and its owners accept the interface records. The maintained allocation already identifies external management, routing, identity, IPAM/DNS, keys, protection and recovery obligations; a code link does not close them. Complete one actual deny-first build, observe its forward/reply and failure paths, prove an isolated restore and data-safe retirement, then evaluate equivalent outcomes on another stack. No site values, firewall vendor, missing original document, risk acceptance or approval are invented here.

[Documentation index](../README.md) · [Maintained design workspace](../current/README.md) · [Existing corrective dispositions](completion-corrections.md)
