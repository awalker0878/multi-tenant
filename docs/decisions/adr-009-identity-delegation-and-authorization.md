# ADR-009 — Identity, delegation and authorization

Owner role: IAM/security leads. Related phases: P00, P01, P02, P06. Record date: 2026-10-05.

Origin: `DIRECTED`. Disposition: `ACCEPTED` for console-managed external OIDC and the local bootstrap administrator lifecycle, as recorded in the [decision register](decision-register.md). Delegation, provider scope, session/freshness bounds and emergency recovery details retain their stated implementation checkpoints.

## Context

A new installation must be accessible before its external OIDC connection exists. Administrators establish that connection through the console. Governance owns identity-connection records, the installation's bootstrap administrator and application authorization; the console owns the administration interface and browser sessions. Authentication alone cannot authorize a native effect.

## Decision and scope

External OIDC is configured and maintained through the console administration interface. Issuer/discovery details, client registration settings and claim mappings are persisted as governed application settings. Client secrets are write-only inputs to protected server-side custody; application records retain scoped secret references. OIDC provider values are not supplied through environment variables, deployment manifests, Helm values or static configuration files. Infrastructure settings such as database connectivity, application encryption keys and workload trust retain their deployment ownership.

On initial deployment, a controlled, idempotent bootstrap operation creates one installation-local administrator with a cryptographically random temporary password. Deployment displays the account name, temporary password and console URL once to the authorized installer. Persist only the password hash and a mandatory-password-change state. Exclude the password from retained/shared deployment logs, container/application logs, telemetry, release artifacts and evidence records.

The first successful login permits only password change and logout. Every protected API and console route enforces this server-side restriction until the administrator chooses a different password. Successful change invalidates the temporary password, rotates session/CSRF state and enables the scoped console administration needed to configure OIDC. The account is not a shared service/worker identity and does not bypass tenant policy or separation of duties.

The local bootstrap implementation uses a ten-minute change-required session and
a thirty-minute absolute setup-session lifetime. Governance retains opaque session
hashes, checks current authority on each protected request and revokes all earlier
local sessions when the password changes. Five failed credential attempts lock the
account for sixty seconds across replicas. Minimal session introspection supplies
the state required to enforce change/logout; it grants no additional function.
See [the bootstrap increment](../implementation/p02-local-bootstrap.md) for the
implemented password policy, deployment binding and measured scope.

Saving provider settings does not complete setup. Test the connection, verify a federated identity and its explicit administrative grant, then activate OIDC and disable the local administrator atomically. Revoke local sessions and delegated authority at that transition. Invalid settings or a failed test leave local setup available after the required password change. Provider failure after activation never automatically restores local login.

Restarts, additional replicas, upgrades and deployment retries must neither recreate the account nor regenerate, redisplay or reset its password. Preserve bootstrap completion and local-account retirement through backup/restore and reconcile their current state before reopening access. Lost-password recovery requires an explicit authenticated operating procedure; it is not a startup side effect.

Initial checkpoint: P02.01/P02.05 implement and qualify deployment bootstrap, first-login enforcement and console OIDC setup before G02. A production OIDC registration is supplied through the console when configuring that installation, not as an input needed to begin P02 development.

Refinement and validation: provider scope, identity/delegation contracts, session and revocation semantics before affected P02.01–P02.04 packages; immediate pre-effect rechecks before P06.03.

## Consequences

- Governance remains the authority for identity connections, local bootstrap state, memberships, grants and approvals. External identity-provider groups do not independently confer product authority.
- The console uses owner APIs; it does not read Governance's database or expose passwords, client secrets or tokens in page props, history or subsequent settings responses.
- Services validate identity and enforce their own resource boundary. Delegated worker authority binds tenant, site, operation, plan revision and expiry.
- Bootstrap and federated login share the required session, request-forgery, throttling and audit controls; local bootstrap is limited to the installation setup period.

## Details to resolve before affected implementation

- The implemented initial profile uses one installation-wide active provider, immutable settings revisions, exact issuer/subject identities and an explicitly named installation administrator. The [federation increment](../implementation/p02-federation.md) records protocol, network and session bounds. Membership administration is separate; provider claims cannot create product grants.
- The [initial data-facing service delegation](../implementation/p02-service-delegation.md) uses distinct mounted workload credentials, opaque sixty-second audience/action/scope-bound handles and uncached current-authority checks. Catalogue registers an owning-service guard; real resource integration follows P03. Operated issuance/custody, durable workflow delegation and pre-effect freshness remain their receiving/P06 checkpoints.
- Federated sessions expire within thirty minutes and the verified ID token lifetime; the initial handover uses its five-minute proof lifetime. Every request reads current Governance authority. Provider-side revocation is bounded by session expiry; provider logout/revocation events and independently controlled emergency recovery remain receiving extensions. Separation of duties and approval expiry are owned by P02.03/P02.04.
- Bind protected deployment credential display and interrupted-bootstrap recovery to each supported installation runtime.

## Acceptance and validation

- Install without OIDC deployment values; observe one random bootstrap credential through the protected deployment channel and only a password hash in persisted state.
- Deny normal console and direct API access before the first-login password change; reject the temporary password afterwards and verify session rotation.
- Configure, test and activate OIDC entirely through the console. Deny unauthorized connection edits and prove client secrets are not returned or logged.
- Preserve local setup after an invalid provider test; after verified federated administrator activation, deny all local login/session/delegation paths, including during an OIDC outage.
- Exercise concurrent deployment, restart, retry, interrupted setup and quarantined restore without duplicate administrators or resurrected credentials.
- Exercise wrong-tenant, expired, revoked and changed-role requests before P02 acceptance; approvals cannot be reused for a different plan or actor scope.
- Recheck authority immediately before native effects, including queued work admitted before revocation.

Record implementation evidence and gate outcomes in the delivery register. This accepted design does not complete a work package or pass G01/G02.

## Revisit conditions

Provider scope, trust, revocation guarantees, administrative delegation or the controlled recovery model changes.

## Related records

- [Decision register](decision-register.md) — decision disposition and checkpoints.
- [Governance](../services/governance.md) and [console](../services/console.md) — ownership and user behaviour.
- [Identity and trust](../operations/identity-and-trust.md) and [installation](../operations/runbooks/install.md) — credential lifecycle and operating procedure.
- [P02](../implementation/phases/p02.md) and [Q01](../qualification/campaigns/q01-contract-and-tenancy.md) — implementation and acceptance.
