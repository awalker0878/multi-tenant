# P02 completion review inputs

The requested continuation is implemented through source `fe88107aac0aca028170fd5f39f06e0b0d30cb7f`.
Its installation notifications, recovery admission and nonempty approval-history
restore pass the three independent browser campaigns in EV-P02-019. The
[engineering assessment](../qualification/gate-reviews/g02-engineering-assessment-2026-10-05.md)
maps the measured results to G02. P02 remains IN_PROGRESS: the existing phase cards,
ADR-009 and frontend requirements include the decisions and observations below.
These are concrete receiving inputs, not a request to reauthorize development.

## Exceptional support access — BL-P02-001

P02.03 requires an explicit privileged support policy; P02.04 requires a
break-glass audit contract. The current permission matrix denies unknown/support
actions and supplies no impersonation, approval override or local-login recovery
endpoint. Existing tenant grants cannot delegate administrative/support authority.

The following is a **policy proposal for IAM/security and Governance review**;
it is not a published API, implemented elevation path or accepted E0 evidence.

| Decision | Proposed contract for review |
| --- | --- |
| Request identity | A current federated subject requests access for a named, different-or-same executing subject; retain requester and executor separately. No shared support account or issuer-group-derived permission. |
| Bound scope | One installation, tenant, explicit site/environment and resource set; an enumerated action list. No wildcard tenant, secret extraction, destructive native action, approval override or implicit resource expansion. Owners must name the initial supported action list before implementation. |
| Approval | A current tenant owner and an independently assigned security approver both approve the immutable request digest. Neither approver may be requester or executor; tenant administration alone cannot appoint the security approver. Actual role-assignment authority must be supplied. |
| Lifetime | Proposed maximum 60 minutes, bounded by every underlying session/grant. Expiry is effective at the exact deadline without a scheduler. No extension in place; a fresh request and approvals are required. |
| Admission and revocation | The owning service checks current subject, both approvals, exact action/resource and current custody at every new admission. Revocation, changed scope or changed approver authority permanently invalidates this request. No cached permit or event confers access. |
| Emergency boundary | Issuer/key/custody loss holds access. Emergency containment may stop admission through separately controlled infrastructure authority; it cannot mint tenant rights or revive a retired local account. Recovery/rebind remains a distinct approved operating procedure. |
| Audit contract | Append `requested`, each attributable `approved` or `rejected`, `admitted`, `denied`, `revoked` and `expired` facts with immutable request digest, policy revision, incident reference, installation/tenant/scope/action, requester/executor/approver references, decision revision, correlation ID and timestamp. No credential, bearer handle, secret or workload payload. Mutation and audit/outbox commit atomically; delivery/revocation preserves committed facts. |
| Review and custody | Independently review every exceptional use and its expiry/revocation. Supply the accountable reviewer, review deadline, retention/sovereignty policy and protected audit destination; this repository does not invent staffed coverage. |

**Required owner decision:** approve or amend the action list, approver assignment,
duration and audit/review custody. Then implement a new versioned owner contract,
state machine and receiving surfaces; qualify two-tenant denial, self-approval,
scope/digest change, expiry/revocation, outage and restored-history cases. Existing
v1 contracts remain immutable. If exceptional access is intentionally excluded,
that requires an explicit scope review of the phase cards; it is not silently
treated as delivered by the deny-by-default behavior.

## Identity and recovery custody — BL-P02-002

The [implemented recovery boundary](p02-identity-recovery.md) requires the external
admission descriptor to be held and rotated before restore. It prevents an older
database from matching current custody; it cannot detect an older database and its
old active descriptor restored together. There is no automatic rebind or reset.

IAM/SRE must provide the following in the restricted installation record, through
OP03/OP06 in [operating inputs](../../release/operating-inputs.json):

| Input | Concrete acceptance observation |
| --- | --- |
| Actual independent custodian, protected descriptor location and change authority | Application identities can only read the descriptor; database restore/retry cannot restore or replace it. Hold/new-epoch installation is independently observed before storage restore. |
| Key/secret service and restore access | The current encryption material is recoverable through approved custody, separate from application backups and runtime credentials. Record protected references, not values. |
| Retirement/revocation records outside the restored store | Compare activation, local retirement, session/grant/approval revocations and authority revisions after the backup point; missing current facts keep admission held. |
| Resumption and lost-bootstrap procedure | Named recovery owner and independent reviewer authorize any reconciled binding or pre-activation lost-password recovery. Record exact source, database capture, descriptor generation, revocation reconciliation and denial checks before reopening. No raw ad hoc database change or startup rebind. |
| Supported ingress/workload/provider topology | Supply real endpoint/trust references and failure/rotation expectations; execute the existing identity denial cases at those boundaries. Production OIDC values still enter through Console, never deployment configuration. |

The hosted evidence already measures all application tables across process restart
and current same-key restore, two terminal approvals and five decision events across
a separate full-schema restore, and stale-bootstrap admission denial. It does not
supply an operating custodian, approve resumption or establish RTO/RPO.

## Managed browser and accessibility scope — BL-P02-003

EV-P02-019 executes both compiled journeys in Chromium, Firefox and WebKit with
no skips, retries or failed browser cases. Those disposable engines are not a
managed-browser support promise. OP07 in the operating inputs requires actual
browser/OS/policy and assistive-technology combinations and support ownership.

Product/quality must select each supported combination and assign a representative
operator/observer. Use this task sheet for each exact build and policy:

| Task | Observation to retain |
| --- | --- |
| First login and password change | Keyboard-only completion, label/instruction/error announcement, logical focus and old-password rejection; no protected bypass. |
| OIDC settings, invalid test and activation | Secret input stays private, validation is announced, draft-preserving notification and explicit refresh work, activation is understandable and retired access is denied. |
| Tenant and membership navigation | Authorized options only; keyboard pagination/focus, zoom/reflow and chosen assistive technology preserve task completion. |
| Denied, expired and conflicted edits | Clear remediation, focused/announced error, no replay under another tenant and no inaccessible blocked control. |
| Multi-tab/history restore | Real managed-browser history/cache eligibility is recorded; session loss or revocation clears/revalidates restored data, and late responses cannot expose the previous scope. |

Record the exact browser/OS/assistive versions, relevant managed policies, tested
WCAG 2.2 AA criteria, task result, defects, observer and evidence references.
Unexecuted rows remain unexecuted; an automated engine pass is not a manual review.

## Receiving decision — BL-P02-004

IAM/security, Governance, SRE and product/quality examine the immutable evidence
using [the G02 procedure](../qualification/gate-reviews/g02.md), record actual
reviewer identities and per-criterion decisions, and close or explicitly re-scope
remaining obligations. G01 receiving conditions carry forward. Codex's engineering
examination supplies neither independent approval nor operating identities.

P03 Catalogue resources/wire integration, the P05.04 real immutable-plan producer
and P06.03 immediate native-effect checks retain their own phase checkpoints. They
are not new prerequisites for completing the P02 synthetic-plan campaign.
