# Threat model

Owner: security architecture, with governance, lifecycle, SRE and application owners. Review scope: R03/R04/R14–R17/R22–R24/R29–R32; P00.05, P02, P06, P10.03. Decision authority and unresolved selections remain in the [decision register](../decisions/decision-register.md).

## Assets and security objectives

Protect tenant intent and membership; immutable plans and approvals; native resource ownership; application datasets and keys; execution grants; workflow/operation history; evidence and qualification decisions; deployment trust and recovery material. Availability includes safely retaining uncertainty and preventing unsafe writes during an outage. An available console with unavailable authorization must not become an execution bypass.

The attacker model includes an authenticated user of another tenant, a compromised service or site worker, a malicious or damaged guest/disk image, stolen administrator credentials, altered artifacts, and a partitioned worker retaining old authority. Accidental retries, stale restores and incorrect ownership are included because their effects can be equally destructive. Platform administrators and key custodians remain privileged trust dependencies; their authority is constrained, attributable and reviewed, not assumed harmless.

## Boundaries

The [deployment model](deployment-model.md) owns the logical flow register. Evaluate browser→console, console→owner API, service→private persistence, service→broker, lifecycle→site worker, worker→native/guest/service API, source→staging→target, evidence producer→assurance/object store, and operations→trust/backup infrastructure separately. Evaluate tenant isolation within each shared component as well as network isolation between components.

## Threat and verification register

| ID / threat | Required prevention or containment | Detection and evidence obligation |
| --- | --- | --- |
| T01 Cross-tenant object access | Owner API evaluates authenticated tenant/resource scope; storage and projections enforce equivalent isolation | Q01: guessed IDs, forged tenant fields, cross-tenant search/export/job/evidence access and service caller tests |
| T02 Confused service deputy | Authenticate workload audience and actor delegation; intersect caller, actor and resource permissions | Q01/Q03: wrong audience, missing actor chain, scope widening and service-only caller denials |
| T03 Stolen or revoked authority | Bounded credential lifetime; current authorization at privileged boundaries; attributable revocation and containment | Q03/Q04: revoke during queued/running operation; measure effect-boundary stop and observe already-dispatched effects |
| T04 Plan/approval substitution | Bind approval, job and operation to immutable plan digest, action, tenant and exact scope | Q03: changed digest, stale input, expired window and retirement under migration-only approval rejected |
| T05 Duplicate or resurrected writer | Durable operation journal; one writer per owned field/resource; effective native fencing and reconciliation | Q04: lost response, duplicated dispatch, old-worker resurrection and restored lease do not duplicate effects |
| T06 Forged or replayed message | Authenticated producer/consumer; validated envelopes; outbox/inbox deduplication; events convey facts rather than authority | Q01/Q04: forged/reordered/replayed events cannot mint approval or redispatch mutation |
| T07 Endpoint or discovery injection | Allowlisted endpoint identity, certificate validation, constrained collector egress and input bounds | Q02: attacker-provided addresses/redirects, unexpected certificates and excessive pages are rejected without credential disclosure |
| T08 Hostile conversion payload | Data-worker isolation, minimal mounts/privileges, bounded resources and authorized data path | Q07/Q08/security exercise: malformed disk/archive, path escape, decompression/resource exhaustion and cross-job access containment |
| T09 Data disclosure or residency escape | Approved transfer/staging/backup locations, encrypted authenticated paths, constrained readers and key custody | Q07/Q09: denied unintended egress, artifact access, staging cleanup and independent object/data-path observations |
| T10 Evidence or support forgery | Producer attribution, verified bytes/digests, append-only decisions and independent qualification review | Q03/Q09: altered object, missing bytes, same-name replacement and self-issued qualification fail admission |
| T11 Supply-chain or configuration substitution | Signed digest-bound promotion, locked dependencies, reviewed config and restricted mirrors | Q09: unsigned image, wrong digest, changed dependency/configuration and untrusted signer rejection |
| T12 Stale restore resurrects authority | Quarantined restore, revocation reconciliation, effective new fencing and native readback before resume | Q09: stale grants/approvals/leases, missing journal and newer native effects remain held |
| T13 Availability or shared-budget exhaustion | Per-tenant/API budgets, backpressure, bounded buffers and failure-domain capacity | Q10: noisy tenant, endpoint throttling, full evidence staging and loss of capacity preserve required safety behavior |
| T14 Target-write loss during recovery | Observe source fencing and target first write; application-approved reconciliation or forward recovery | Q07: post-cutover target changes survive recovery; old-source restart cannot silently discard them |
| T15 Privileged support misuse | Time-bounded scoped access, separate approver/acceptor roles and protected accountability | Q01/Q09: ordinary support cannot approve its own elevated action or retrieve arbitrary tenant secrets |

These entries define required analysis and tests. They do not assert that controls have been implemented or that residual risk has been accepted.

## Security decisions that block unsafe effects

Before enabling native writes, the accountable owners must select credential expiry/revocation bounds, time-skew policy, effective old-worker fencing, mandatory evidence/audit failure behavior, data-worker isolation and source/target recovery boundaries. Link each selection to its ADR, implementation and negative test. A queue name, namespace, certificate alone, or database epoch cannot substitute for these controls.

Before accepting a deployment, record the actual administrative jurisdiction, hosting/backup/staging locations, support access, key custody, trust roots and recovery dependencies. Evaluate them against the selected assurance profile. Do not infer sovereignty from the location of the control-plane server alone.

## Findings and change workflow

1. Record a finding with threat ID, affected release/tuple/tenant scope, reproducible conditions, evidence reference, impact, likelihood basis and accountable remediation owner.
2. Identify the affected gate and support claims. Mandatory control failures hold the corresponding admission or promotion scope; retain unaffected scope only with an explicit impact decision.
3. Specify containment and expiry, fix or accepted constraint, tests and independent reviewer. An exception includes accountable owner, rationale, compensating controls and review deadline.
4. Reproduce the issue safely in the qualified test boundary, implement remediation and run affected positive, negative and recovery tests.
5. Preserve the original finding and append closure evidence. Documentation edits or a scanner result alone cannot close a native-behavior finding.

Review this model when an API trusts a new caller, a context changes data ownership, a worker gains a capability, a transfer method or platform tuple changes, or recovery alters authority. Revisit relevant threats after an incident and before release acceptance. Raw payloads, secrets and sensitive topology belong in restricted evidence records.
