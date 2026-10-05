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

1. Run `services/governance/database/migrations/001_identity.sql` as
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
Record observed runs and source bindings here and in the delivery register after
execution; the presence of a workflow is not a passing result.

Next: persist one installation-wide external OIDC connection through Console
administration, write-only secret custody, strict provider/token validation,
authorization-code/PKCE/state/nonce controls, tested explicit federated admin
grant and atomic activation/retirement. A failed test must preserve local setup;
activation must revoke all local authority, including during an IdP outage.
The `retired` state already denies local login/session/rebootstrap, but setting
that state in a test does not implement or qualify federated handover.
