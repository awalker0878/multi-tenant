# Mobility review verification — 1 October 2026

This is a revision-specific delivery record, not the active backlog or a release
approval. The [B01–B50 execution plan](../product/enterprise-workload-mobility-execution-plan.md)
and [capability review](platform-capability-review-2026-10-01.md) own current scope.

## Delivered revisions

| Revision | Change |
|---|---|
| `9d4c6685b6fd0fcb6df211aebd47857562265456` | Audited starting revision on `implementation/all-waves`. |
| `b993470a35e832621270aa437ba7113a1650dd84` | Strict bounded OpenStack allocation/image/attachment facts, selector 2 with no selector-1 alias, and pure/TLS regressions. |
| `249d75ff760d11d57fc02dd9f6aecef31d217eb6` | Single typed catalog requirement owner, cross-profile obligations, removal of redundant validation/unused constant, and regressions. |
| `60d6b1375a0633adfc882ef2805e8028be8e031b` | Availability catalog 18, regenerated digest-bound examples, consolidated current plan and six synchronized maintained design records. |

The alignment result tree is `34e5c2e964c28ad3fef4daa89b8f4d6a914b899a`.
Its 34-file plaintext patch has SHA-256
`fcdc9f79c04d795c090d9308910290825ade1052e19282a9f16434abb2a19909`.
A one-use branch-scoped application checked exact input/output identities and
ordinary nonforce push conditions, then removed its workflow in the result commit.
The resulting tree was read back from GitHub and matched the locally tested tree.
No additional writer workflow remains. That application is not a test or release gate.

## Observed local tests

Python 3.13.5; synthetic fixtures and loopback HTTPS, not deployed vendor systems.
Counts below are independent suite results and must not be added to the broader
run as though they were unique tests. This record does not claim final-revision CI.

| Check | Observed result | Scope / limitations |
|---|---|---|
| Discovery suite | 525 tests, OK, no skips | Includes 15 new OpenStack hardware/reference tests and existing signed HTTPS/custody regressions. Run on the discovery increment; later changes do not modify those owners. |
| Profile/policy suite | 84 tests, OK, no skips | Includes 12 new test methods with adversarial subcases; final catalog revision 18. |
| Golden replay suite | 25 tests, OK, no skips | Final regenerated five-request/three-platform examples and digests; plans remain disabled. |
| Provisioning documentation suite | 41 tests, OK, no skips | Includes the corrected catalog/profile version matrix. |
| `scripts/check_documentation.py` | 37,549 checks passed, zero failures | Alignment tree; frozen transcription integrity, source relationships, links and maintained records. Not external-source or native validation. |
| `scripts/check_repository.py` | Passed; empty issues list | Alignment tree; structural checks. Not Terraform/Ansible engine execution. |
| Staged whitespace validation | Passed | Alignment tree. |

Reproduction commands:

```sh
python -m unittest discover -s tests/provisioning/discovery -p 'test_*.py'
python -m unittest discover -s tests/provisioning/policy -p 'test_*.py'
python -m unittest tests.provisioning.end_to_end.test_golden
python -m unittest discover -s tests/provisioning/documentation -p 'test_*.py'
python scripts/check_documentation.py
python scripts/check_repository.py
```

## Broader-run limits and corrections

The broad local provisioning run discovered 1,988 tests and ended with **three
assertion failures, eight import errors and 113 skips**. The three failures were
stale availability catalog/profile versions in the documentation matrix. Those
entries were corrected, and the complete 41-test documentation suite then passed.
Do not relabel the original broad run as a pass.

Eight modules could not import optional `psycopg` or `temporalio` dependencies.
The pinned dependency installation attempt failed because this local environment
could not resolve the package index. Database-role, Temporal and other skipped
integration results are therefore not supplied by the local run. The existing
repository CI must be checked at the final revision for installed-package,
PostgreSQL, Temporal, engine and other integration results; an older successful
run or an empty commit-status list is not a substitute.

## Acceptance boundary

No VMware, Nutanix or OpenStack installation was contacted or qualified. No native
migration, HA/DR campaign, production activation, architecture approval or operating
acceptance was issued. Main was not merged, and draft PR 54 remains a review surface.
B05, complete Wave 2 workflows and Waves 3–6 remain open as detailed in the plan.
Frozen source records, original signed evidence and historical commits are retained.
