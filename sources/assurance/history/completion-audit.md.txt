# Completion-audit corrective release

This response separates repaired repository defects from native implementation,
qualification and governance decisions that cannot be manufactured by documentation.
Original audit: [CA-01–CA-11 original report (plain-text provenance)](../../sources/assurance/completion-audit-original/COMPLETION_AUDIT.txt).

| Finding | Change in this release | Remaining acceptance boundary |
| --- | --- | --- |
| CA-01 Code fidelity | Preserve Word line breaks/tabs in code; independent exact code comparison and command-token regression | Historical code examples remain historical, not executed native plans |
| CA-02 Semantic checks | Compare ordered table cells; exact ADR record/page/index/crosswalk agreement; negative mutation cases | A checker does not authenticate a human approval or prove arbitrary semantic correctness |
| CA-03 Integrity command | Archive old manifest; current source manifest generated after reviewed changes; test published command | Hash consistency is not authenticity or authorization |
| CA-04 Markdown workflow | Maintained block amendments with source identity, replacement, reason, owner and review status; refresh refuses maintained files | Actual normative adoption is separately recorded |
| CA-05 ADR lifecycle | Proposed/Accepted/Rejected/Superseded, accountable role and consistent governance metadata with reciprocal supersession | All actual current source-derived records remain Proposed |
| CA-06 Missing source family | Explicit source-scope decision record, available views and recovery/replacement path | Original RAD/TAD family still unrecovered; owner scope decision remains open |
| CA-07 Historical findings | Individual F01–F24 current-applicability, owner-role and remaining-evidence records | No old schema bug or live obligation falsely closed |
| CA-08 Verification families | Complete CT, RA, W14 and Q11 indexing; full RA records in active Markdown | Original not-run status retained; overlapping procedure counts are not test passes |
| CA-09 Implementation allocation | All 194 original requirements mapped to 370 proposed assertion focuses, enforcement loci, roles, artifacts, external/unimplemented controls and evidence limits | Actual site configuration, native evidence and accepted applicability remain open |
| CA-10 Root schema boundary | Validate roots without backend; export schemas only from matching backend-free modules | Actual engine run must verify current source; no production backend access |
| CA-11 Exact engine/lock evidence | Run the corrected source in connected CI and retain actual provider locks and exact commit checks | Consult PR/check-run results for executed status; no native platform/authorization claim |

## Additional source-backed decisions

The protected-state, cryptographic profile and portability/exit ADRs are expanded
with explicit audit-remediation proposals. Two new proposed records cover independent
telemetry/collection loss and governed images/privileged dependencies. None is marked
Accepted because the user requested a source merge.

## What can be closed by this release

Conversion, command-path, consistency and indexing defects can be closed when their
new tests pass on the final source. Source recovery, organizational adoption, actual
control implementation and native qualification cannot be closed by those tests.
The [assertion allocation](implementation-allocation.md), [historical dispositions](historical-findings.md)
and [source scope](source-scope.md) keep those obligations visible.

## Verification and evidence

`python scripts/check_documentation.py` performs independent table/code comparison,
ADR governance/page checks, amendment checks and all existing link/source checks.
`python tools/check_local.py` includes negative mutations and verifier command tests.
`python tools/verify_terraform.py --mock-tests` exports actual provider schemas only
from modules and validates roots with backend disabled. The read-only CI tests run
without native platform credentials. A temporary preparation job, if used to publish
generated files/locks, is restricted to the correction branch and removed before merge.

Actual engine run and merge identifiers belong to GitHub's current checks and PR;
this document does not predeclare them successful. Native production tests are not run.
