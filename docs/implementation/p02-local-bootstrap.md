# P02 local administrator bootstrap

Owners: Governance and Console; packages P02.01/P02.05; requirements R03/R31;
criteria G02.01/G02.03/G02.04; campaign Q01. Scope: the local administrator and
mandatory first-login password change. External OIDC and the other P02 packages
remain in progress or queued under [the phase card](phases/p02.md).

## Implemented boundary

- Governance's controlled migration creates one installation sentinel. The
  `identity:bootstrap` deployment command locks it, generates a 192-bit random
  temporary password, persists an Argon2id hash and mandatory-change state, and
  displays the account/password/console URL through an interactive terminal.
  Redirected/noninteractive output is refused before mutation. Retries do not
  regenerate or redisplay the password.
- Local login creates an opaque, Console-audience session, retained as a SHA-256
  hash in Governance. Change-required sessions expire after ten minutes; setup
  sessions have a thirty-minute absolute lifetime. Governance reads current
  identity/session state on every authority check. Only change/logout and minimal
  session introspection are available until the password change succeeds.
- A new password must differ and contain 15–128 characters, with a 512-byte
  server limit. Changing it verifies the current password, increments credential
  version, revokes every earlier local session and issues new authority in one
  transaction. Five failed attempts lock the account for sixty seconds across
  replicas. Local setup grants no tenant or native-operation authority.
- The Console uses its own encrypted server-side session store and an independent
  mounted workload credential to call Governance. It rotates session and CSRF
  state on login/change, rechecks owner authority on protected requests and
  excludes credentials from page props, flashed input and logs. Actual web routes
  use Laravel's CSRF middleware and reject unexpected Host values.
- Identity transitions append audit and outbox rows in the same transaction.
  Runtime SQL grants cannot delete/recreate the sentinel or update/delete audit.
  Outbox transport/delivery is still future work; durable rows are not a claim
  that a consumer has received events.

The implemented [HTTP contract](../../contracts/openapi/governance-local-identity-v1.json)
belongs to Governance, with Console as its consumer. Browser authority never
substitutes for the mounted Console workload identity. Replacing/removing that
file revokes the workload credential on the next request. Service trust uses
deployment bindings; external OIDC provider/client values do not.

## Deployment binding

1. Apply Governance migrations in numeric order, currently `001_identity.sql`,
   `002_federation.sql`, `003_tenancy.sql` and `004_approvals.sql` under
   `services/governance/database/migrations/`, as
   `governance_migrator`, with the existing `governance_owner`/`governance_runtime`
   database roles and `app` schema. Run Console's `001_shared_state.sql` under
   its separate migration identity. Application startup never runs either.
2. Mount a Console-specific random credential of at least 32 URL-safe characters
   in both peers and set `CONSOLE_CREDENTIAL_FILE` to the mounted path. Supply
   Console's canonical `APP_URL`, `GOVERNANCE_URL` and optional
   `GOVERNANCE_CA_FILE`. Non-loopback Governance URLs require verified HTTPS;
   health tokens are not accepted. Existing database and application-key custody
   remain required.
3. As the authorized installer, with terminal/session recording disabled, run
   `php artisan identity:bootstrap --console-url=https://<console-host>` in the
   Governance container through the runtime's interactive exec facility. Both
   input and output must be terminals. Do not pipe the operation into deployment
   logs, CI, `tee`, a transcript or an artifact. The protected display is a
   deployment step, not a container startup side effect.
4. Sign in as `admin` at `/login`, then change the password at `/password`.
   `/setup` becomes available only after the owner accepts the change. Preserve
   the sentinel, credential version, hashes, sessions and ledger in recovery
   inventory. There is no automatic reset or lost-password recovery command.

An interrupted display after commit requires the separately authenticated
recovery procedure; rerunning deployment cannot reveal/reset the password.
Actual Compose/Kubernetes installer integration, protected terminal custody and
quarantined restore remain receiving verification before operated deployment.
Do not attach existing P01 candidate signatures or image qualification to new
P02 bytes.

## Verification and next increment

The source includes direct API tests, mandatory-change/session/throttling and
transaction-failure cases, actual-route CSRF/Host tests, frontend checks, and a
dedicated PostgreSQL/browser workflow. The latter uses the pinned disposable
PostgreSQL image, two simultaneous deployment terminals, runtime role denials,
migration replay, real HTTP contract validation and the compiled Console journey.
[EV-P02-001](../../verification/p02/identity/run-37324210957/report.json) records
32 passing checks at source `007cb7e4fe63ac3a851793682258ffe1d7fb6a57`:
nine PostgreSQL feature tests (82 assertions), one compiled Chromium journey,
verified database TLS, simultaneous terminal bootstrap, replay/role denials,
API schemas, password/session transitions and credential-log exclusion. The browser
run has no skips, retries or failures. The retrieved ZIP digest and all six retained
artifact digests match; all 165 bound source files match the delivered application.
The [retrieval record](../../verification/p02/identity/retrieval.json) identifies
both immutable archives. The first run stopped before Console startup because
its database fixture lacked Console's required TLS/mounted-password bindings;
that failure remains [retained](../../verification/p02/identity/run-37323186027/report.json).

Local full suites passed 46 Governance and 60 Console tests, both language-boundary
and type checks, the frontend build/type checks, and 89 documentation/control tests.
Hosted package/image replays use the subsequent packaging source
`ebec6eeb9589ba2b184ba64ac57c69f43bee44c6`; the 165 identity campaign inputs remain
unchanged. The migration explicitly revokes broad foundation default grants before
assigning least privilege. New image input registration and canonical Console host
bindings are included; existing P01 results are not reused for changed bytes.

All ten [affected regression workflows](../../verification/p02/regression-runs.json)
pass at `ebec6eeb9589ba2b184ba64ac57c69f43bee44c6`, including all nine independent
package and image jobs, Compose, Kubernetes, HTTP contracts, messaging, stateful
dependencies, Permit Desk recovery and documentation/policy checks. These results
retain their development scopes and do not pass G01/G02 or authorize promotion.

The subsequent [federation increment](p02-federation.md) implements Console-managed
connection settings, write-only secret custody, strict token validation and tested
atomic handover. EV-P02-002/003 retain its distinct observations, including the
compiled HTTPS/PKCE browser journey. The [tenant/approval increment](p02-tenancy-and-approvals.md)
and [next-work queue](../../next_work.md) track the current continuation. Historical
retired-state seed tests remain narrower than actual federation evidence.
