# P02 service actor delegation and owning-service guard

Owner: Governance/IAM and Catalogue. Packages P02.01/P02.03; requirements
R03/R04/R32; G02.01/G02.03; Q01.01/Q01.02/Q01.08/Q01.11.
This is an implemented initial data-facing profile for receiving review, not an
approved native-admission or exceptional-access policy.

## Issuance and current authority

The [new HTTP contract](../../contracts/openapi/governance-delegation-v1.json)
requires the Console workload credential and current federated user session to
issue a random opaque delegation. Only its SHA-256 is persisted. The credential
binds one tenant, target service, named action and exact site/environment/resource
scope. It expires within sixty seconds and the source session's remaining lifetime.
At most 1,000 live credentials per source session can exist. There is no refresh,
offline validation, redelegation or browser token exposure. Issuance retry creates
another bounded credential; domain mutations retain their independent idempotency.

| Audience | Permitted delegated actions |
| --- | --- |
| Catalogue | `application.read`, `application.write` |
| Planning | `plan.read`, `plan.create` |
| Assurance | `evidence.read` |

This audience map restricts existing actor permissions; it does not grant them.
Administrative, approval-decision, support and native-operation delegation remain
denied. Local setup accounts cannot issue tenant delegations.

Only the independently authenticated target service can resolve a credential.
Every resolution reads current session, provider revision, actor, tenant,
membership/grant scope and fingerprint. Logout, expiry, actor disablement,
membership/grant changes, suspension, explicit revocation or workload-key rotation
deny use. Regranting membership cannot revive a credential bound to its old
revision. Issuer changes fail the current-provider join. Missing custody and
ambiguous shared service keys fail closed.

The originating federated actor may explicitly revoke its own delegation, even
after losing membership. Another actor cannot inspect or revoke it. Repeated
revocation is idempotent. An immutable receipt and the existing identity
audit/outbox commit together; raw credentials never enter them. The identity
outbox uses [its own versioned delivery contract](p02-identity-events.md),
separate from tenant facts and current authority.

## Workload custody and Catalogue boundary

Governance mounts separate `CATALOGUE_GOVERNANCE_CREDENTIAL_FILE`,
`PLANNING_GOVERNANCE_CREDENTIAL_FILE` and
`ASSURANCE_GOVERNANCE_CREDENTIAL_FILE` values alongside its existing Console
credential. Files are reread on each request; the initial delegation binds their
current hashes. These are workload trust settings, never OIDC provider settings.
Actual issuance/custody/rotation ownership and independent restore epochs remain
OP02/OP03 receiving inputs. Do not reuse retired credentials.

Catalogue registers the `delegated:application.read` / `application.write`
middleware and its private Governance client. An inbound request needs both a
separate Console-to-Catalogue workload credential and the actor delegation.
Catalogue uses its own workload identity over verified HTTPS to resolve the
delegation, never forwards a browser session, rejects redirects and validates the
returned audience/actor/tenant/action/scope/expiry. It accepts no cached result;
the immediate response must be at most five seconds old. Its sixty-five-second
upper expiry tolerance bounds transport/clock variation, not token issuance.
Operated clock monitoring is still required.

The middleware derives scope from server route parameters, takes the action from
route registration and clears its immutable actor context after every response or
exception. The resource-owning Action must also query its own tenant/site/environment
and resource relationship before reading or mutating data. An upstream allow
cannot make a foreign resource belong to the requested tenant.

Catalogue configuration uses `CONSOLE_CATALOGUE_CREDENTIAL_FILE`,
`GOVERNANCE_URL` (HTTPS origin), `GOVERNANCE_CREDENTIAL_FILE` and optional
`GOVERNANCE_CA_FILE`. Inbound and outgoing credentials cannot be identical.
There is no shared administrator, health-token or local-password fallback.

## Verification and remaining integration

Governance feature cases exercise exact scope and audience, wrong tenant, missing
credentials, source-session expiry/logout, disabled actors, credential rotation,
membership revocation/regrant, explicit revocation, forged authority fields and
issuance rollback. EV-P02-005 retains the PostgreSQL identity campaign at
`5bc32839ae7dedd186fca68e429e5effa723222d`: 80 feature cases (1,427 assertions),
including thirteen delegation cases, with 247 matching source bindings and six
retained artifact hashes. The hosted Catalogue package replay passes all 50
feature cases (207 assertions), formatter, static analysis and dependency checks;
its 153 source bindings and 34 artifact hashes match.

Catalogue's HTTP-adapter/middleware cases use an explicit test-only owner route
and fake Governance transport. They verify independent credentials, repeated
current checks, stale/malformed responses, redirect denial and the owner's separate
tenant predicate. These are local boundary tests, not a deployed cross-service
business journey. No test route is shipped by the application. P03 binds the
guard to real Catalogue resources; Planning/Assurance adopt the contract with
their own private clients as their product APIs appear. Python wire/client
qualification and the real cross-service campaign remain open.

P05.06/P06.03 still own exact-plan native admission, durable workflow delegation,
fencing and pre-effect revocation checks. The current sixty-second credential is
never queued as long-running execution authority. Exceptional support access and
restore/revocation reconciliation require the distinct reviewed contracts;
development implementation does not supply those approvals or pass G02.
