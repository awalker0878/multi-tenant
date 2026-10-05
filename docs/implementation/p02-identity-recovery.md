# P02 identity recovery admission

Owner: Governance/IAM and deployment custody. Packages P02.01/P02.03; criteria
G02.01/G02.03/G02.04. This is an implemented fail-closed boundary. Actual independent
custody, permission to resume a restored installation, and G02 receiving remain open.

## Boundary

Governance requires a deployment-owned admission descriptor mounted at
`GOVERNANCE_IDENTITY_ADMISSION_FILE`. This is infrastructure recovery custody, not
OIDC configuration: issuer, client, secret and claim settings remain Console-owned
application settings. The descriptor contains exactly `version` (1),
`installation_id` (UUID), `epoch` (64 random hexadecimal characters), `state`
(`active` or `held`) and `bootstrap_allowed` (boolean), encoded on one JSON line.
The runtime reads it on every admission. Missing, malformed, held or mismatched
custody returns `identity_recovery_required` with HTTP 503 and no-store headers.

Migration 009 creates a singleton binding with no initial value. The protected
bootstrap command can set its hash only within its existing locked transaction,
when the administrator is uninitialized and external custody explicitly permits
bootstrap. It then creates the one temporary credential as before. Normal requests,
startup, migration replay and an already initialized installation cannot bind or
rebind restored authority. Withdraw `bootstrap_allowed` after initial deployment.
No password, issuer or provider secret is included in the descriptor or binding.

HTTP user and service entrypoints, direct session resolution, local login, OIDC
flows and delegated inspection check current admission. OIDC checks again after
remote exchange before issuing identity. The boundary prevents **new admission**;
operators must drain already admitted requests before changing/restoring storage.
Background audit/outbox delivery can preserve already committed custody facts;
notifications never authorize a restored session or privileged command.

## Recovery protocol and limits

Before restoring any application state, the independent custodian holds admission,
withdraws bootstrap permission and installs a new recovery epoch outside the
application backup. Drain both applications and restore in isolation. Even changing
the new descriptor to active cannot match an older database binding, recreate a
local administrator or revive a session. Retain the restored state and reconcile
retirement, current revocations, membership/grant revisions and approvals against
independent current records before any separately authorized rebind.

There is deliberately no automatic rebind, reset-password or break-glass endpoint.
An existing pre-009 installation is held until its owner provides a reconciled
migration binding; migration never silently adopts its authority. The descriptor
must be mounted read-only for application processes and controlled outside the
application database, backups and deployment retries. An old database **and** an
old active descriptor restored together cannot be detected by this mechanism.
Independent custody and a correct restore procedure are mandatory, not inferred
from the disposable fixture. This is not a distributed retirement journal or a
complete independent revocation authority.

## Verification

Focused feature cases exercise missing/malformed/held/cross-installation/changed
custody, direct session and HTTP denial, normal bootstrap retry, withdrawn initial
bootstrap permission, and refusal to bind existing or restored state. They also
verify no automatic mutation of the saved binding on denial.

The hosted campaign captures private PostgreSQL archives before activation and
of both complete application schemas after the browser journey. It compares
row counts and deterministic hashes for every owned table after process restart
and same-key current restore. It then loads the older bootstrap snapshot under
held/new custody and verifies login, existing-session, OIDC-flow and interactive
bootstrap denial. Archives and raw table bytes never enter retained evidence.
Only hashes, counts, redacted results and source identities are retained. Empty
tables remain visibly empty; this does not infer exercised approval history,
broker-store recovery, HA, accepted RTO/RPO or operating custody.

The terminal approval-history fixture additionally produces one rejected and one
revoked decision through real owner actions with distinct synthetic author/reviewer
identities. A separate process observes both rows and five approval audit events;
the campaign restores the complete fixture schema and compares every owned table.
It does not substitute a test plan for the future P05 producer or resume restored
authority. Results are counted only after the changed-source campaign executes.
