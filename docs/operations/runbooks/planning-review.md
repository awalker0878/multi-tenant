# Planning assessment and immutable review

Use this procedure for P05 review deployments. The phase supplies no native
execution path. Preserve the P01 health probes' explicit readiness limitation;
use authenticated owner checks and the P05 qualification campaign to examine
review availability. Production readiness, support and P06 admission need their
own operating evidence.

## Configure independent owners

Apply Planning's owned SQL migrations as its migrator; runtime uses only the
explicit grants. Apply Governance's existing identity/delegation migrations and
source-owner routes. Do not grant Planning access to a sibling database.

Every service connection uses verified HTTPS with an absolute mounted CA path.
Planning needs `GOVERNANCE_URL`, `CATALOGUE_URL`, `INVENTORY_URL`, `ASSURANCE_URL`
and the corresponding `_CA_FILE` variables. Supply distinct
`PLANNING_{GOVERNANCE,CATALOGUE,INVENTORY,ASSURANCE}_CREDENTIAL_FILE` mounts.
`PLANNING_CONSOLE_CREDENTIAL_FILE` and
`PLANNING_GOVERNANCE_READER_CREDENTIAL_FILE` authenticate its two callers; the
reader credential is separate from Planning's outgoing Governance identity.

Console configures `PLANNING_URL`, `PLANNING_CA_FILE` and
`PLANNING_CREDENTIAL_FILE`. Catalogue and Assurance each configure their own
`PLANNING_CALLER_CREDENTIAL_FILE`, `GOVERNANCE_URL`, `GOVERNANCE_CA_FILE` and
`GOVERNANCE_CREDENTIAL_FILE`. Inventory configures
`INVENTORY_PLANNING_CREDENTIAL_FILE` alongside its existing owner credentials.
Governance configures its recognized workload identities and the Planning reader
URL/CA/credential. An unavailable owner or revoked actor never uses a cached allow.

Mount `PLANNING_REGISTRY_FILE` as a read-only absolute path, at most 512 KiB:
`schema_version: 1`, named `profiles`, named `policies`, and exact
`tenant_id/site_id/endpoint_id` assignments selecting one of each. Each profile
has platform, version and all eleven dimension declarations. Each policy pins
its revision, expiry, mandatory requirements, compiler/adapter/automation/contract
SHA-256 values, downtime bound, reservation owners, exact saved Terraform plan,
toolchain, backend/workspace/lineage/serial/lock owner and sole field writers.
A missing assignment fails closed. Treat policy/profile changes as new immutable
versions; retain prior versions for reproducible review. The synthetic fixture
illustrates the shape and supplies no deployable production inputs.

Assurance independently mounts `ASSURANCE_QUALIFICATION_REGISTRY_FILE`, at most
512 KiB, with `schema_version: 1` and `records` conforming to the
[qualification schema](../../../contracts/schemas/planning/qualification-v1.json).
Only independently authorized Assurance custody publishes or revokes a dossier.
Exact scope includes tenant/site/endpoint/native scope/installed tuple, action,
method, profile and artifacts. E3/E4 evidence must actually exist, be current and
unrevoked. The HTTP endpoint is read-only; absent records return explicit unknown.
Duplicate matching records or malformed custody files are unavailable. Replace
mounted files atomically and retain version/change records.

## Review a plan

1. Open the immutable Catalogue revision and choose **Compare destinations and
   plan**. Select one to three authorized sites/endpoints/current generations.
2. Inspect declarations, observations and qualified support separately. Explain
   each mandatory unknown, unsupported capability, custody/isolation gap and
   capacity deficit using its requirement, source and remediation.
3. Compile the chosen candidate with exact executors and authority lane. Inspect
   content and approval digests, mappings, artifacts, expiry, destructive effects,
   budgets and the target-first-write recovery boundary. A held proposal remains
   inspectable and grants no authority.
4. Compare another plan by identity to inspect changed paths. A new plan identity
   has its own approval binding even when semantic content is equivalent.
5. Request approval only while the current view and submitted digest agree.
   Governance still requires independent approval and current operator validation.
   P06 must repeat source, entitlement, qualification, reservation and approval
   checks atomically at admission and immediately before effects.

After an uncertain response, retry the original command unchanged. Do not generate
a fresh key to guess whether a prior command committed. A revoked session or
scope clears protected review access. Polling clears stale eligibility and disables
approval; create a new assessment/review after material input or event changes.
P04's currently unassessed observations remain held rather than implying support.

## Facts and recovery

Use the combined [broker definitions](../../../deploy/dependencies/stateful/planning-facts.json)
when enabling P03/P04/P05 facts together. Separate historical imports overwrite
Planning's one per-vhost permission row. Provision users independently; do not
embed credentials in definitions. Planning may read only `planning.inventory` and
`planning.intent`, and write only `planning.events`. The durable
`assurance.planning` queue retains facts for a later Assurance consumer; P05 does
not claim that consumer is implemented. Retention and queue capacity are operating
inputs, not a license to silently drop unconsumed facts.

Set `PLANNING_BROKER_HOST`, `_PORT`, `_CA_FILE` and `_PASSWORD_FILE`; run
`planning-facts publish`, `planning-facts inventory` and `planning-facts catalogue`
as separately supervised bounded processes (`--limit` 1–100). Publisher confirms
precede delivery receipts. Lost confirmation/receipt replays the original event
ID; consumers commit deduplication and invalidation before acknowledgment.
Inspect owned outbox/delivery/inbox/invalidation records and quarantine digests.
Never refresh source expiry or delete immutable history to clear a hold. Correct
owner inputs and create a new assessment. Backups must include immutable records,
command receipts, outbox and inbox together; exercise restore before operation.

Lifecycle persists local reservation intent before owner allocation. Reconcile
unknown outcomes by stable reservation identity. Compensate only known, currently
unused owner receipts; expiry alone cannot release live consumption. The P05
adapter is a separately controlled simulation. P06 must supply authenticated
native owners and atomic admission/command receipt/reservation binding/outbox
records, including current approvals and immediate effect rechecks.

## Qualification

Run `python scripts/p05/generate_contracts.py --check`. The P05 workflow retains
strict lint/types, real PostgreSQL journal races, verified TLS source/approval
traffic, confirmed broker delivery and the compiled Console in three engines.
Source/log/archive hashes and negative results accompany the receiving packet.
Automation supplies no representative operator or designated reviewer signature.
