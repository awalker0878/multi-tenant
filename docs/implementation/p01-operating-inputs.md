# P01 operating inputs and admission activation

P01.04/P01.05/P01.06; G01. The [machine-readable receiving record](../../release/operating-inputs.json)
routes the remaining actual inputs to the existing P00 field IDs. The recorded
G00 decision remains accepted. These fields are not another request for that
approval and do not reopen the independent development baseline.

## Facts established by this increment

- The [repository observation](../../verification/p01/admission/repository-observation-2026-10-05.json)
  records `protected: false`, no rulesets, default branch `main` and connector account
  administration permission. The repository API reports public visibility. No
  protection/ruleset mutation or workflow-dispatch operation is exposed by the
  connector. Account permission alone is not an available mutation capability.
- Independent development image sources and locks are pinned. The artifact campaign
  creates SBOMs, scan/database identities, source/lock provenance and real signatures,
  then exercises receiving-side denial. Current base-image findings hold every
  candidate. Fresh ephemeral signing keys and synthetic receivers establish no
  operated signer, custody service, route owner or accountable acceptance.
- GitHub check runs identify the PR head while the jobs check out a test merge.
  Stable jobs therefore retain an exact checkout record; admission validates its
  ZIP digest, workflow, job, attempt and base/head/test-merge binding. A head-only
  green check is insufficient. Missing artifacts or stale attempts deny admission.
- The new pull_request_target hook is absent from `main`, so the first draft PR did
  not trigger it. The separate push probe checks target-base execution as a bounded
  experiment. It is not installed repository admission.

## Remaining receiving inputs

Supply sanitized identities and immutable evidence references in the record;
credentials and restricted addresses stay in the existing custody system.

| Record | Actual input still needed | Accountable owner |
| --- | --- | --- |
| OP01 | Target runtime/dependency BOM, allowed traffic, mirrors, disconnection/freshness limits | SRE/platform |
| OP02 | Registry transfer path, signer/custody identity, independently delivered trust root, revocation and promotion owner | Platform/security |
| OP03 | Secret, PKI and evidence services; rotation, retention, key recovery and access ownership | Security/IAM/records |
| OP04 | Numeric GitHub IDs and logins for context/platform/architecture/security/SRE roles; independent reporting identity and installed settings | Repository administrator/review owners |
| OP05 | Real alert-route reference, response rota, escalation, receipt and acknowledgement evidence | SRE/service owners |
| OP06 | Complete recovery/retained-state inventory, deletion authority, recoverable keys and attributable acceptance | Application/SRE/security/records |
| OP07 | Patch/support access owners and managed-browser/assistive matrix | Engineering/SRE |

`python3 scripts/p01/admission/operating_inputs.py` currently returns HELD with all
seven records missing or unreviewed. It validates record completeness and existing
field references; it does not authenticate people or read protected custody.
Even a complete input record does not authorize promotion. The artifact verifier
continues to deny operated scope until an actual approved trust integration exists.

The validator now fixes each OP record to its exact carried field inventory,
rejects hidden values/review data on UNKNOWN records, mutable or mismatched Git
evidence revisions, credential-bearing references, duplicate evidence and future,
unattributed or non-UTC reviews. REJECTED observations remain held. Ten negative
and completeness fixtures exercise these boundaries; fixture people confer no role.

Ordinary CI checks record validity and permits honest UNKNOWN entries. The gate
readiness command is `python3 scripts/p01/admission/operating_inputs.py --require-complete`;
it exits unsuccessfully while any of the seven actual inputs remains unreviewed.
Passing record validation must never be represented as passing this readiness check.

## Prepared repository settings

The [candidate protection body](../../release/branch-protection.candidate.json)
specifies strict required checks from the observed GitHub Actions application,
administrator enforcement, two current approvals, approval of the latest push,
CODEOWNERS review, resolved discussions, linear history and disabled force pushes
and deletion. It is an incomplete activation candidate: it intentionally contains
only observed check contexts. It must not be applied as a complete admission policy.

Before activation, bind real role accounts in `release/review-policy.json` and
generate CODEOWNERS from those verified identities; no role label can be inserted
as a GitHub login. Install the trusted trigger through the governed default-branch
path. Publish its exact-head decision through the approved reporting identity,
then add that verified context/application to protection. A workflow's automatic
default/base-commit result is not sufficient proof of a current PR-head decision.
Retain API settings and real missing/failed/stale-check, insufficient-role and
direct-push denial observations after activation. CODEOWNERS alone does not enforce
the complete affected-owner and independent security role predicates.

The exact destination is the `greenfield/enterprise-microservices-plan` branch in
`awalker0878/multi-tenant`. The reviewed body is intended for GitHub's
[update branch protection API](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection).
No settings, default-branch source, role assignment or operating service was changed
by preparing this package. BL-P01-001 remains open until actual activation is observed.
