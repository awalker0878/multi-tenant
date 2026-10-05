# P02 bounded support and break-glass policy

On 2026-10-05 the requesting owner approved the decision and implementation:
“Yes support/break-glass policy decision, followed by its implementation. Add this to the code securely”.
This accepts the exceptional-access direction proposed at `16fbd1b70d35db9fccc222eb6c70668fdf9907fa`.
The conservative initial action set and executable rules below make that direction concrete.
This is authorization to implement; it does not supply an independent G02 reviewer,
production custodian, staffed coverage, retention decision or recovery-resumption approval.

## Policy version 1

| Boundary | Required behavior |
| --- | --- |
| Initial actions | `support.membership.inspect` and `support.grant.inspect` return whitelisted Governance-owned diagnostic fields for explicitly named records. The executor may lack ordinary tenant membership. These actions supply no subject identifiers, credentials, secret values, impersonation, approval override, native effect or general tenant permission. |
| Request | Current federated tenant member, explicit named executor, one tenant/site/environment, at most 20 named resources and the allowlisted actions. Immutable binding includes installation recovery binding, tenant revision, requester/executor, policy version, expiry, reason code and bounded case reference. No wildcard, in-place extension or resource expansion. |
| Role assignment | A freshly authenticated federated installation administrator explicitly appoints another federated actor as a security approver or reviewer for one exact tenant/site/environment, for at most 30 days. Tenant administration cannot appoint security authority. Installation administrator status alone cannot inspect tenant support history. |
| Approval | A current scoped `tenant_admin` and a current explicitly assigned security approver both approve the exact digest. Neither can be requester or executor, and one actor cannot occupy both roles. Each decision binds its session, current authority, current resource versions and expiry. |
| Activation | The named executor explicitly activates after both approvals using a freshly authenticated federated session. That exact session remains bound; a new login cannot silently renew the request. Approval and activation receipts are status observations, never bearer permits. |
| Lifetime | Maximum 60 minutes, shortened to requesting membership/session, both approving authorities/sessions and executor session. Admission stops at the exact deadline even if the scheduler is stopped. Fresh login means less than five minutes old for request, assignment, approval, activation and review. |
| Admission | Every diagnostic read rechecks the current actor, both approvers, memberships/assignments, sessions, provider revision, currently published signer material, Console workload credential, tenant/resource revisions and recovery binding. The result leaves the owner only after its audit/outbox admission commits. |
| Failure and revocation | Issuer/JWKS, encryption custody or external recovery-custody failure holds new access. No offline cached-key fallback, bootstrap revival or deployment OIDC override. Explicit rejection/revocation and authorized history reads can proceed during provider outage under current local federated admission; recovery hold still denies them. Detected authority change terminally invalidates the request. Regrant does not reopen it. |
| Post-use review | Every used request requires one immutable review by an explicitly assigned security reviewer distinct from requester, executor and either approver. Review follows terminal expiry/revocation/invalidation, is due within 24 hours of effective expiry, and overdue review blocks new activations by that executor. Outcome is `acceptable` or `incident` with an external case reference. |
| Bounds | 20 new requests per requester/hour; 100 role assignments per installer/hour; 1,000 diagnostic admissions per request; 60 attributed request-denial events per actor/minute; 100 audit entries per keyset page. Exceeding the denial-event budget never rolls back expiry/invalidation. Invalid authentication, malformed input and undiscoverable requests use ordinary redacted request telemetry rather than falsely attributed support facts. |
| Audit | Append-only requested, approval, activation, admitted/denied, rejection, revocation, expiry, invalidation and review facts, plus role-assignment/revocation facts. Each has internal actor/resource/tenant references, revision, policy revision, per-event correlation UUID and timestamp; request facts bind the immutable digest. Audit/outbox writes share the owner transaction. Runtime cannot rewrite/delete binding, approvals, reviews, audit or outbox payload. |
| Delivery | A dedicated restricted audit queue receives minimal immutable fact references and a canonical audit hash. Notifications are at-least-once, unordered and never authority. Revocation does not suppress historical delivery. Case references, request scopes, sessions and secrets are excluded from broker payloads. |

The policy concerns a Governance API workflow. No Console support screen or
browser support journey is claimed. Its server-to-server ingress requires both
Console workload identity and the current federated actor session. Workload
credentials must never be exposed to browser code. OIDC provider values remain
Console-managed application data; no deployment inputs were added.

Existing sessions predating signer retention can continue their ordinary lifecycle.
They must authenticate again before exceptional support operations can validate
the original verified signing material against the issuer's current keys.

## Receiving and operations

The implementation must qualify independent approval, exact binding, two-tenant
and cross-scope denial, expiry, changed/revoked authority, issuer/key/custody outage,
atomic audit, concurrent owner decisions, durable event delivery and nonempty
terminal history after restore. Existing published contracts remain unchanged;
new support OpenAPI/AsyncAPI/JSON Schema artifacts have their own versioned names.

Actual security approvers/reviewers, incident references, audit destination custody,
retention/sovereignty and response ownership must be supplied by the installation.
A configured role or synthetic test identity does not establish human independence
or staffed incident coverage. Recovery still uses the independent admission epoch
and the separately approved resumption procedure. Restoring old data and its old
custody descriptor together is outside the recovery fence's guarantee.

See the [P02 completion review](p02-completion-review.md) for the remaining operating
and receiving inputs. P02 and G02 remain governed by their delivery register and
receiving review, not by this policy approval alone.
