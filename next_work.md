# Current next work — Capability runtime assurance (PR #64)

> **Authoritative queue for this branch.** Other handoffs below are archived
> background and must not override this queue. Update this section whenever
> a task is completed, blocked, or newly discovered. Branch:
> `codex/capability-runtime-assurance-audit-fixes`; review:
> [PR #64](https://github.com/awalker0878/multi-tenant/pull/64); base `main`.
> Keep the PR **draft**; no automatic merge or native production activation.

**Source baseline:** `09a5285cdb74808d927a9be3720ac636451f07a6` at this queue's
creation (2026-10-08). Follow-on commits supersede this SHA. All statuses
below mean **engineering implemented / unverified** unless an exact-source
CI result or independent native evidence is linked. E2 fixture success is
not E3 native proof; E3 native proof is not E4 receiving acceptance.
Check the updated `git rev-parse HEAD` and the
[PR checks](https://github.com/awalker0878/multi-tenant/pull/64/checks)
at every checkpoint.

## Active, prioritized work queue

| ID | Priority | Owner / boundary | Status | Required next action and completion evidence |
| --- | --- | --- | --- | --- |
| CT-N01 | P0 | Engineering / CI | **BLOCKED: queued** | Obtain a finished result for **every required check** on the exact PR head, including Assurance PostgreSQL, P05 Planning, Lifecycle, Inventory and capability assurance. Fix the actual failures, rerun, attach exact run/job URLs, no skipped or unrun mandatory checks. All 39 checks on head `7a17079c396dcb1d39b7c038fdf3cddf1a56f667` were queued when last inspected. |
| CT-N02 | P0 | Assurance + Planning / PostgreSQL | **Implemented, unverified** | Run disposable PostgreSQL migrations `services/assurance/database/migrations/002_qualification_authority.sql` and `services/planning/migrations/003_qualification_invalidations.sql` from scratch; confirm least-privilege role grants, append-only history, epoch triggers, outbox/inbox commit-before-ack, atomic failure and rollback. Retain tests and full execution logs. |
| CT-N03 | P0 | Planning / P05 CI | **Implemented, unverified** | Prove `scripts/p05/qualify.py` and P05 live jobs exercise the new qualification inbox, read-boundary guards, concurrent plan-save/revocation and tenant isolation; run Ruff format/lint, mypy and the database tests. Capture source-bound pytest/JUnit artifacts and fix failures. |
| CT-N04 | P0 | Assurance → Planning / E2 composed delivery | **PARTIAL: real Planning DB/ASGI replay test committed** | Provision **disposable** HTTPS/TLS peers and independent tokens; publish a real Assurance SQL event, relay, persist Planning inbox, return exact durable receipt, and deny/hold affected execution. Test lost response, same-event replay, stale/out-of-order epochs, conflicting identity, tenant isolation, TLS failure, sink outage and restart. No accepted E2 cross-service result yet. |
| CT-N05 | P0 | Security / receiving trust | **OPEN** | Commission TLS certificate/SAN/CA, distinct caller secret custody, network-only ingress authorization, bounded retries, audit logs, receiver ownership and replay/quarantine policy. Verify no reviewer/observer/owner token reuse. The private endpoint is **code only**. |
| CT-N06 | P0 | Planning/Lifecycle / fail-closed authority | **PARTIAL** | Test every approval, execution, native effect, placement, and retry boundary against **current** Assurance authority, not only a cached hint. Ensure delayed/missing invalidations and unknown scope always hold. Add cross-service revocation between preflight and effect and revoked approval replay. |
| CT-N07 | P1 | Assurance + Planning / contract | **Implemented vectors, unverified** | Prove byte-for-byte PHP/Python canonical scope hash and wire schema compatibility for representative Unicode/slashes, installed tuple, tenant, action/method, null decisions, and epochs. Reject unrecognized/changed event contracts; preserve append-only event IDs. |
| CT-N08 | P1 | Capacity owners / P07 | **OPEN** | Replace proposed/synthetic capacity with operated owner-backed **exclusive** reservations per physical CPU, memory, storage and address source; check source generations and native readback; verify collision, expiration and multi-owner compensation. No fabricated physical capacity receipt. |
| CT-N09 | P1 | Native VMware → OpenStack / E3 | **NOT RUN** | Enroll installed-source tuple, export/export lease, guest OS/driver/UEFI, disk conversion/import, native target and independent observer receipts; run selected `VM_COLD_EXPORT` positive, refusal, resume and rollback cases under approved authorization. Do not infer native support from test fixtures. |
| CT-N10 | P1 | Native network/isolation/recovery / E3 | **NOT RUN** | Qualify real IPv4/IPv6 flows, VRF/VPC tenancy, return paths, ingress/egress, RBAC, keys and storage, topology/fault domains, failure-trigger RTO/RPO, application/dependency recovery and source/target fences with independent observations. |
| CT-N11 | P1 | Assurance reviewer + receiving owner / E3/E4 | **NOT REVIEWED** | Obtain evidence-bound independent E3 reviewer decisions and E4 receiver sign-off on actual native recovery, service ownership, accepted residual risks, monitoring and operating runbooks. Missing credentials/decision authority cannot be replaced by mock acceptance. |
| CT-N12 | P1 | Platform governance / shadow adoption | **OPEN** | Read-only shadow comparison of qualification decisions, profile/adapter behaviour and native outcome changes; reconcile false confidence, stale qualification and method catalogue differences. Record rollout/rollback gates, versioned replay and promotion authority before any cutover. |
| CT-N13 | P1 | Verification / A01–A16 | **PARTIAL** | Build and run the complete source-bound acceptance matrix with positive, negative, timeout/retry, cross-tenant, authority-revocation and native-effect cases. Map each A01–A16 to code, test and evidence in the implementation ledger; do not close an A-ID with a mere fixture. |

## Execution sequence and handoff rules

1. **Repair and verify P0 correctness first:** CT-N01–N03, including real
   PostgreSQL roles/migrations and both languages' format/type suites. CI
   runs must bind the source SHA of the actual commit being reviewed.
2. **Prove composed invalidation:** CT-N04/N05 and cross-boundary CT-N06,
   then CT-N07 contract parity. Durable receive acknowledgment is the
   only delivery success; no response or ambiguous reply stays pending.
3. **Complete provider-backed native work:** CT-N08–N10. Never use
   synthetically generated receipts as capacity exclusivity or native proof.
4. **Accept or explicitly deny promotion:** CT-N11–N13 with actual owners
   and independent reviewers. E2 green never implies E3/E4 release.

### Status and evidence conventions

- **Implemented, unverified**: committed code exists but source-bound
  passing tests are missing. **PARTIAL**: some paths exist, gates remain.
  **OPEN/NOT RUN**: required integrated/native work not performed.
  **BLOCKED**: an external prerequisite or queued CI prevents proof.
  Mark **DONE** only with exact source SHA, command/workflow run URL,
  negative/recovery results, owner and reviewer where applicable.
- Update this file first for the next handoff; add durable observations to
  [the assurance delivery ledger](docs/implementation/capability-runtime-assurance-ledger.md)
  and commissioning directions to
  [the invalidation runbook](docs/operations/runbooks/qualification-invalidation.md).
  The P05 workflow, Assurance PostgreSQL workflow and native qualification
  evidence remain separate gates.
- Distinguish **code committed**, **CI passed**, **E3 accepted** and
  **E4 commissioned** in both the PR body and the tracker. Do not
  auto-enable the scheduled relay, assert native support, close the delivery
  ledger or merge PR #64 before all mandatory gates are complete.

---

## Implementation checkpoint — current PR #64

Engineering changes made in this continuation (GitHub commits, **not** a green
workflow or external native/receiving acceptance):

- `0de8e22b`, `4981e2b3`, `e8bd963e`: established this authoritative
  13-item queue; archived previous handoffs without losing historical content.
- `918a269e`: authenticated Planning ASGI receiver backed by a real
  PostgreSQL fixture; tests commit-before-HTTP-ack, lost-response replay,
  conflicting event ID, and cross-tenant hold isolation.
- `824bc476`, `66810472`, `aebac503`, `6ff4ee05`: independent canonical
  scope SHA-256 goldens shared between Python and PHP (including Unicode and
  slashes); add both language suites to their existing E2 verification lanes.
- `ac2cb9cb`, `7a17079c`: Assurance HTTPS publisher rejects incomplete,
  unexpected, mismatched state/operation and malformed tenant/scope wire bytes
  *before* any request; adapt positive and negative Pest fixtures.

**Current CI evidence:** latest inspected branch head
`7a17079c396dcb1d39b7c038fdf3cddf1a56f667`, PR #64, 118 commits,
39 checks queued and zero completed confirmations. Do **not** mark CT-N01,
CT-N02, CT-N03, CT-N04 or CT-N07 DONE. The Planning ASGI/PostgreSQL test is
not a commissioned HTTPS Assurance-to-Planning service campaign. Independent
E3/E4 proof and provider-backed capacity remain outstanding.

## Retained historical handoffs

The previous 38 KB of P0/P01–P10 handoffs, other branch baselines and
related receiving obligations is preserved, without rewriting its content, in
[archived-next-work-handoffs.md](docs/implementation/archived-next-work-handoffs.md).
Those descriptions are not current PR #64 statuses. Return to this file for
the active tracked blockers and next steps.
