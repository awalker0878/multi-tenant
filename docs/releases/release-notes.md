# Release notes and support communication

Owner: product/delivery lead with operations and qualification reviewers.

Release notes explain what users can do with a particular accepted artifact set, what changed, what limitations apply and how operators can install or upgrade it safely. They must agree with the release manifest and evidence-backed support scope.

## Required content

| Section | Content and review rule |
| --- | --- |
| Release identity | Release/candidate ID, date, manifest reference and accepted operating scope |
| User outcomes | Concrete available workflows and changes to user-visible behavior |
| Supported combinations | Exact operation/direction/method/guest/deployment scope or link to its current authoritative records |
| Changes | New behavior, corrected defects, permission/approval changes and operator impact |
| Compatibility | Required dependency/client/worker versions, migration sequence and retirement of old contracts |
| Installation/upgrade | Required readiness, admission pause points, runbook references and expected service impact |
| Recovery | Rollback limits, forward-recovery requirements and data/writer implications |
| Known limitations | Unsupported cases, unresolved non-blocking issues and practical consequences |
| Security and trust | Changes requiring access/key/certificate/policy action; protected details use approved channels |
| Support | Receiving service ownership, incident entry point and necessary diagnostic/evidence references |

Distinguish a product feature from a newly qualified platform combination. A new adapter, profile row or passing simulator campaign cannot be described as general native support. Avoid vendor-wide statements where evidence covers only one installed tuple or method.

## Publication checks

Check that every capability statement has a support record, that changes are described in user/operator terms and that all linked instructions match the release. Remove sensitive endpoint, tenant and credential details. Confirm accessible wording for error/recovery actions and explicit downtime or compatibility impacts.

Keep corrections attributable and preserve prior release notes. When a support record is withdrawn or materially narrowed, publish the changed effect on users and the required operating action; do not leave an older broad support statement unqualified.
