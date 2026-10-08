# P02 console-managed federation

Owners: Governance and Console. Packages P02.01/P02.05; requirements R03/R31;
criteria G02.01/G02.03/G02.04; campaign Q01. This increment implements external
OIDC setup, tested handover, federated sessions and revisioned provider updates.
P02 and G02 remain open for the complete tenancy, authorization, approval,
integration and receiving scope.

## Implemented behavior

One installation-wide connection has immutable settings revisions and a separate
active pointer. Console setup persists the issuer, client ID, an exact stable
administrator `sub`, and optional permitted private IPv4 networks through
Governance. The canonical Console callback URL is derived server-side from its
installation origin. No provider value is read from deployment configuration.

Client secrets are write-only. Settings hold UUID custody references; a separate
Governance table retains authenticated ciphertext under its application encryption
key. Blank secret input retains custody only for the same issuer and client.
Secrets, tokens, PKCE verifiers and test proofs are excluded from page props,
flashed input, audit payloads and HTTP error messages. The existing application-key
custody and recovery obligations apply; this is not an external vault integration.

Saving settings does not activate them. The five-minute authorization-code flow
uses S256 PKCE, a random state and nonce, and a random browser binding held only in
the Console's encrypted server session. Governance hashes state and binding,
encrypts its verifier/context, and consumes the attempt before token exchange.
It validates a signed RS256 ID token against the configured issuer's keys, exact
issuer and client audience, authorized party where required, expiry, issuance and
recent authentication time, nonce, and stable subject. Provider groups and email
addresses confer no product roles.

A setup test must authenticate the explicitly named administrator. It produces a
five-minute proof bound to that actor, settings revision and initiating session.
Activation rechecks current authority and the proof under database locks, changes
the active revision, retires the bootstrap account, destroys its password hash,
revokes every local and prior federated session, and appends audit/outbox records
in one transaction. Audit failure rolls the transition back. The new Console
session and CSRF token rotate. The initial handover session lasts only until the
proof expires; subsequent provider sign-ins last at most thirty minutes and never
outlive the verified ID token. There is no refresh-token storage.

Draft edits leave the existing active connection and sessions available. A new
successful test is required to activate a new revision. Failed setup leaves the
changed-password local account available. Provider failure after activation cannot
recreate it. Every protected request checks current Governance state; ordinary
federated users cannot administer the identity connection. Provider-side logout
and asynchronous provider revocation are not implemented: local session revocation
is immediate, while provider revocation is bounded by the existing session expiry.

## Provider and network boundary

The initial supported protocol profile requires HTTPS discovery, authorization,
token and JWKS endpoints on the issuer's origin, `code`, S256, RS256 and
`client_secret_post`. Subjects are exact issuer/sub pairs. Additional origins,
algorithms, client authentication methods and tenant-specific providers require a
separate implemented and qualified extension; they are not silently accepted.

Outbound requests validate all DNS results and pin the selected address through
cURL; proxies and redirects are disabled. TLS certificate/hostname checks remain
enabled and responses are bounded to 256 KiB and eight seconds. Public addresses
are accepted; RFC1918 addresses require explicit console-managed CIDRs. Loopback,
link-local, metadata, multicast and reserved addresses cannot be opted in. Internal
provider certificates require the runtime's approved system trust chain. The
Console callback permits loopback HTTP only for the existing isolated test runtime.

## Delivery and verification

Apply Governance migration `002_federation.sql` after `001_identity.sql`, using
the controlled migrator. Runtime SQL roles cannot rewrite settings revisions or
delete identity audit. Preserve settings, encrypted custody, active revision,
actors, sessions, attempts and proofs with the existing quarantined-restore rules.
A historical backup is never permission to reopen retired local access.

The [federation HTTP contract](../../contracts/openapi/governance-federation-v1.json)
defines the Console-owned workload caller and separate user-session requirements.
`/setup` renders save/test/activate controls; `/identity/callback` consumes the
server session binding and returns a clean URL without reflecting provider data.

Local Governance tests exercise real RSA signatures through the actual provider
adapter with synthetic HTTP responses, including wrong issuer/audience/nonce,
expired or missing claims, wrong administrator, forged signature, replay, expiry,
revision/session substitution, provider failure and transactional rollback.
Console tests exercise real CSRF middleware, safe props, failed callback, secret
flash exclusion and session rotation. These tests do not establish interoperability
with an operated identity provider, real provider DNS/TLS, supported deployment
handover/restore, complete accessibility or G02 acceptance. Retained campaign
results and exact source bindings are recorded separately in the delivery register.

Primary protocol references: [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html),
[Discovery](https://openid.net/specs/openid-connect-discovery-1_0.html),
[OAuth security BCP](https://www.rfc-editor.org/rfc/rfc9700.html), and the
[locked JWT library](https://github.com/googleapis/php-jwt/tree/v7.2.1).

## Retained qualification

EV-P02-002 retains the earlier PostgreSQL adapter/compiled bootstrap regression.
EV-P02-003 adds the actual compiled Console setup, wrong-administrator denial,
HTTPS/PKCE token exchange and atomic handover against a disposable provider.
Governance verifies the fixture certificate authority; only the disposable browser
context accepts the self-signed certificate. Four exchanges and credential-log
exclusion pass. This proves the exercised transport/flow, not operated-provider
interoperability, DNS/key rotation, full restore, production topology or receiving
acceptance. Exact reports and source bindings are in the delivery register.
