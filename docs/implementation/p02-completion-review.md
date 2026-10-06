# P02 completion review inputs

The support/break-glass implementation is complete for the accepted bounded
policy at `ad53968f4f3f4c9c1bc031a17f909be4ff6dabf2`. EV-P02-020–022 retain
the user decision, local checks and corrected-source hosted qualification: all
three engines pass 116 checks, including nonempty support history restore; the
separate TLS event campaign passes 74 cases. BL-P02-001 is resolved.

The [engineering assessment](../qualification/gate-reviews/g02-engineering-assessment-2026-10-05.md)
maps the evidence to G02. Recovery source `7ec7a60` additionally passes all three
156-check custody/resumption campaigns, retained in EV-P02-023/024.
**P02 remains IN_PROGRESS and G02 NOT_REVIEWED** pending
the actual custody, managed-browser/accessibility and independent receiving inputs
below. These are concrete operating/review obligations, not a request to reauthorize
the completed implementation.

## Exceptional support access — BL-P02-001 resolved

The requesting owner approved the support/break-glass policy direction and its
secure implementation on 2026-10-05. The [accepted policy version 1](p02-support-access.md)
records that instruction, the initial exact-record diagnostic actions, distinct
tenant/security approval, maximum one-hour lifetime, live authority checks,
immutable audit and independent post-use review. Existing tenant permissions do
not delegate support authority, and published v1 contracts remain unchanged.

The decision and bounded implementation are complete. The [owner API](../../contracts/openapi/governance-support-v1.json)
implements request, two independent approvals, explicit executor activation, exact
record inspection, rejection/revocation, expiry and separate post-use review.
Immutable history, current-key/custody checks and restricted outbox delivery are
qualified in the [retained index](../../verification/p02/support/qualification-index.json).
The [operations runbook](../operations/runbooks/support-access.md) describes use and
containment. No Console support screen or native writes are claimed.

Actual operator identities, audit custody/retention and independent receiving
acceptance remain operating inputs below. No policy approval is inferred for
production resumption after recovery.

## Identity, support-audit and recovery custody — BL-P02-002

The [independent custody and resumption mechanism](p02-recovery-custody.md) now
implements the requested procedure. A separate custody tool holds/rotates admission;
two distinct enrolled signing keys approve exact restored-state reconciliation;
an owner-only command revokes stale authority; a second two-person approval and
separate custodian release are required before fresh OIDC sign-in. Migration 011
prevents runtime rebinding or writing recovery receipts/releases. Current credentials
must be unique and must not reuse any prior workload credential. No automatic rebind
or local-bootstrap reset is available.

Follow the [executable runbook](../operations/runbooks/identity-recovery-custody.md).
Its software procedure is delivered; actual independent people, keys, host/mount/backup
separation, records and supported topology still require the operating observations
below. Restoring an old database together with its entire old active custody/trust
store remains outside the filesystem fence.

IAM/SRE/security/records must provide the following in the restricted installation record, through
OP03/OP05/OP06 in [operating inputs](../../release/operating-inputs.json):

| Input | Concrete acceptance observation |
| --- | --- |
| Actual support approvers/reviewers and audit custody | Supply accountable identities, exact scoped role appointments, protected `support.audit` consumer/destination, retention/sovereignty, case/review ownership and escalation. Verify actual custody separately from the disposable broker ACL checks. |
| Actual independent custodian, signers, protected store and change authority | Enroll the actual verified recovery owner and a different security reviewer with separate encrypted keys. Only the public directory is mounted read-only into Governance. Demonstrate runtime cannot write custody and that database/application restore cannot roll back its host, keys, journal or descriptor. Independently observe hold/new epoch before restore. |
| Key/secret service and restore access | The current encryption material is recoverable through approved custody, separate from application backups and runtime credentials. Record protected references, not values. |
| Retirement/revocation records outside the restored store | Compare activation, local retirement, session/grant/approval revocations and authority revisions after the backup point; missing current facts keep admission held. |
| Executed resumption and lost-bootstrap disposition | Execute the delivered hold → prepare → two signatures → apply → separately signed resume → confirm → custodian release procedure on the actual isolated installation. Retain exact source/archive, current records, denial checks and fresh sign-in. Lost pre-activation bootstrap remains held; use the accountable clean-installation/data-recovery decision or a separately reviewed design, never reset a retired local administrator. |
| Supported ingress/workload/provider topology | Supply real endpoint/trust references and failure/rotation expectations; execute the existing identity denial cases at those boundaries. Production OIDC values still enter through Console, never deployment configuration. |

The hosted evidence already measures all application tables across process restart
and current same-key restore, two terminal approvals and five decision events across
a separate full-schema restore, and stale-bootstrap admission denial. The new support
campaign additionally restores one used revoked request, two approvals, one independent
review and ten immutable audit/outbox facts, comparing every owned table. It does not
supply an operating custodian, approve production resumption or establish RTO/RPO.
The recovery qualification additionally executes the real owner role and custody CLI,
encrypted-key signing, preserved recovery receipts/releases and fresh HTTPS OIDC
admission; its synthetic identities do not replace these operating assignments.

## Managed browser and accessibility scope — BL-P02-003

EV-P02-022 reexecutes both compiled journeys in Chromium, Firefox and WebKit with
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
remaining obligations. The user-approved policy decision is retained in EV-P02-020;
it does not need to be requested again. G01 receiving conditions carry forward. Codex's engineering
examination supplies neither independent approval nor operating identities.

P03 Catalogue resources/wire integration, the P05.04 real immutable-plan producer
and P06.03 immediate native-effect checks retain their own phase checkpoints. They
are not new prerequisites for completing the P02 synthetic-plan campaign.
