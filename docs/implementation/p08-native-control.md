# P08 native control composition

This increment supplies the native Lifecycle process, current owner clients and the
Planning-to-Lifecycle resolver. It does not supply an installed VMware/OpenStack
pair, a provider fencing service, application protocols or native G08 observations.

## Deployed entry points

Run `lifecycle-native serve --config /run/lifecycle/native.json` for the verified-TLS
native grant boundary and campaign/observation interfaces. Run `lifecycle-native
dispatch --config /run/lifecycle/native.json` separately for Temporal dispatch and
campaign admission. The simulation operation routes are absent from this process.
Database schemas, roles and the independently held custody epoch must already be
commissioned; startup never installs an epoch or grants itself database authority.

The version 1 process configuration contains exactly `schema_version`, `owners_file`,
`tls_cert_file` and `tls_key_file`. All files are bounded protected absolute paths.
Temporal uses `TEMPORAL_TARGET`, `TEMPORAL_NAMESPACE`, `TEMPORAL_CA_FILE`,
`TEMPORAL_SERVER_NAME` and `TEMPORAL_CREDENTIAL_FILE`. Configure the existing
Lifecycle database and Console/Governance request credentials independently.

The owner file contains `schema_version: 1`, `expires_at`, `owners`, `assignments`
and `workers`. `owners` contains exactly `planning`, `governance`, `inventory`,
`custody` and `observer`. Each endpoint contains `origin`, pinned numeric `address`,
`ca_file` and `credential_file`; only verified HTTPS is supported. Credentials for
all owners, outbound workers and inbound workers must be distinct. Rotation is
read on every request; a change during an owner read discards its result.

Each assignment contains `tenant_id`, `plan_id`, `plan_revision`, `plan_digest`,
`approval_id`, `actor_id`, `executor_id`, `campaign_id` and `epoch`. It selects current
records; its presence does not approve or qualify them. Each worker entry contains
`tenant_id`, `executor_id`, `endpoint` and `caller_file`. Campaign members resolve
only an exact assignment. Unknown, expired, removed or ambiguous assignments hold.

## Owner boundaries

| Owner | Current read and validation |
| --- | --- |
| Planning | Existing execution-plan API; recompute binding/content digests, require operational lane, no holds, exact native recipe/scope/custody, named executor and current expiry |
| Governance | New `native-approval-checks`; independently approved operational plan, live executor/requester/reviewer memberships, unchanged approval authorities, current Planning binding and expiry |
| Inventory | New `/internal/tenants/{tenant}/migration-inputs/{application}/{environment}/{site}/{revision}/{digest}`; exact current confirmed review, all disks/datasets/objectives and native source/target identity |
| Custody | Commissioned `/v1/native-custody/epoch` and `/v1/native-custody/checks`; current epoch, installed qualification, ownership, artifacts, state, campaign, provider fence and stop status |
| Observer | Commissioned `/v1/native-observations`; complete independent before/after stage cases, exact intent/binding, fresh evidence and required policy outcomes |

Governance's receipt is explicitly `authority_use: native_approval` and
`native_write_authorized: false`. It is consent, not an effect grant. The native
coordinator combines it with the current native custody boundary and independently
read Inventory records. Simulation approval receipts are rejected.

The new Governance and Inventory interfaces have separately versioned OpenAPI
contracts. Previously published contract bytes remain unchanged. Planning also rechecks recipe revocation on unattended execution and Governance
binding reads. Request/approval APIs do not accept a browser-supplied native plan or credential.

Inventory requires `INVENTORY_NATIVE_READERS_FILE`. It contains `schema_version: 1`
and `grants`. Each reader grant has `reader_id`, a distinct `token_file`,
`expires_at` and `scopes`. Every scope contains exactly `tenant_id`, `application_id`,
`environment`, `site_id`, `revision` and `digest`. One reader can read several exact
commissioned reviews for bulk campaigns. Scope is checked before and after reading
Inventory. This grants neither Inventory editing nor platform write permission.

## External custody and observation protocols

These endpoints require actual implementations administered independently of the
native writer. They are not simulated by this increment.

`GET /v1/native-custody/epoch` returns `epoch`, `evaluated_at` and `expires_at`.
Evaluation must be no older than five seconds and expiry must be in the future.

`POST /v1/native-custody/checks` receives `{plan, binding}`. Return the exact
binding/plan/configuration/tuple/epoch/executor fields and current status required
by `lifecycle.domain.native_workflow.current_authority`. Do not accept caller
assertions as observed provider state. The adapter separately establishes current
Planning, Governance and Inventory facts. Native qualification and provider-side
exclusion/drain remain the custody implementation's responsibility.

`POST /v1/native-observations` receives `{plan, binding, phase}` and returns
`{records}`. Each record follows `lifecycle.domain.native_workflow.observations`:
case, phase, binding digest, intent digest, commissioned independent observer ID,
observation/expiry timestamps, outcome, evidence digest and policy results. Missing
cases, a writer used as observer, wrong digests and stale observations hold the stage.
These current reads remain separate from a worker's process receipt.

## Remaining commissioning

Mount actual source/target endpoint policies, protected account custody references,
approved recipe artifacts and the selected workload's protocols. Confirm G07 entry,
then execute Q07.01–Q07.10 with independent native evidence and record G08 receiving.
No configuration file or software test substitutes for those observations.

## Explicit long movement budgets

Export-archive, copy-conversion and image-import stage intents accept version 2
with `max_seconds` from 1 to 86,400. Version 1 retains its existing 600-second
maximum. The immutable intent still pins the chosen budget, and every effect/chunk
continues to check current authority. The shorter plan, credential, profile or
campaign expiry always wins. A larger budget does not refresh stale observations.

The native worker HTTP wait and Temporal effect timeout follow the grant's remaining
lifetime with a maximum one-day effect budget. Temporal records a patch marker so
retained histories preserve their prior timeout commands. Automatic effect retries
remain disabled. Converter CPU limits follow the explicit remaining budget; file,
memory, output, rate and sandbox isolation limits remain enforced.

This removes the arbitrary ten-minute software ceiling. It does not implement
crash/byte-range transfer resumption. An interrupted NFC or Glance operation remains
held until independently reconciled; re-running a claimed operation, discarding its
spool or extending its expiry is not recovery. Native route-specific continuation
still needs implementation and testing against the commissioned provider protocol.
