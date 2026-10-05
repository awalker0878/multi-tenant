# Observability and alerting

Owners: SRE for collection/routing; each service owner for meaningful signals; security for audit; lifecycle for operation truth. Scope: R15–R17/R29–R31/R34; P01.06, P06 and P10.01/P10.04. [Operating targets](../product/operating-targets.md) and ADR-017 govern accepted numeric objectives.

## Signal contract

Every request, admitted job and native attempt carries stable correlation identifiers across its permitted service boundaries. Use request/trace ID, environment, context, artifact revision, tenant scope, job ID, operation/attempt ID and plan digest where applicable. The authenticated owner determines tenant and actor identity; incoming arbitrary trace fields never confer authorization.

Keep native operation outcomes separate from request success, workflow progress and support status. An HTTP timeout or unavailable worker is an unknown observation, not proof a native operation failed. Dashboards must display missing/stale telemetry explicitly and preserve held/unknown work until reconciled.

| Signal | Required use | Constraints |
| --- | --- | --- |
| Metrics | Availability, latency, rates, queue/backlog age, resource saturation and bounded operational counts | Bounded labels; no per-job/native-object IDs or unbounded tenant labels without a reviewed cardinality budget |
| Structured logs | Attributable decisions, failure diagnosis and transition references | Redact secrets, guest payloads and unnecessary personal data; restrict tenant-sensitive access |
| Traces | Request→service→workflow/attempt correlation and dependency latency | Sampling must not replace durable operation/audit records; avoid secret-bearing spans |
| Audit | Grants/approvals, admission/effect authority, privileged support, qualification and retention changes | Protected append/custody policy; attributable actor and decision revision |
| Evidence | Independent native/application outcomes and gate/campaign results | Finalize through assurance; telemetry transport success is not evidence acceptance |

## Indicators and response

| Scope | Indicator / alert condition | Initial response and accountable owner |
| --- | --- | --- |
| Console/API | Authorized synthetic journey fails; accepted latency/error objective exceeded | Distinguish UI/session, identity and owner-API failure; SRE with affected service owner |
| Governance/trust | Decision unavailable; denied use of revoked authority; excessive clock skew or expiring required identity | Hold affected privileged admission; IAM/security and governance |
| Inventory | Incomplete generation, stale coverage, scope drift or endpoint budget exhaustion | Keep missing facts unknown; prevent affected placement; inventory/platform owner |
| Planning | Required input stale, qualification invalid or eligibility repeatedly blocked | Show exact missing/rejected input; planning/assurance; do not weaken policy to clear alert |
| Outbox/inbox/broker | Oldest undispatched/unprocessed record exceeds bound; dead letters or poison-message growth | Preserve records; inspect producer/consumer compatibility; service owner/SRE |
| Lifecycle/Temporal | Queue age, stuck safe point, replay failure, journal/history mismatch or unknown outcome | Hold affected resource scope; reconcile before retry; lifecycle/SRE |
| Worker/native | Worker trust/heartbeat failure, fencing conflict, native throttling or orphaned effect | Check actual authority and endpoint state; quarantine conflicting writer; platform/lifecycle |
| Reservations | Renewal failure, nearing expiry, exhausted staging/retained-source capacity or allocation mismatch | Hold new effects; reconcile live use before release; authoritative resource owner |
| Evidence | Finalization failure, missing bytes, digest mismatch, staging/backlog bound reached | Quarantine bad artifacts; hold dependent completion/activation; assurance/security |
| Persistence/recovery | Replication/backup failure, restore verification stale, key unavailable or capacity exhausted | Protect recoverability and admission; database/key owner/SRE |
| Data/cutover | Transfer stalls, integrity/consistency check fails or writer fencing cannot be observed | Stop cutover advancement; retain source/target state and involve application owner |
| Alert pipeline | Missing delivery/acknowledgement of synthetic alert or collector heartbeat | Use independent escalation route; telemetry owner; do not declare healthy from absence of alarms |

Thresholds are versioned environment configuration with units, evaluation window, minimum sample size, severity, recovery condition and owner. Derive freshness/expiry alerts from remaining safe authority or data budget; select paging thresholds using measured behavior and accepted objectives. No example number in a design becomes a promised service level.

## Alert payload and routing

An actionable alert carries stable alert ID, first/last observation, environment/component, affected authorized scope, observed value and threshold revision, signal freshness, user/safety impact, correlation references, runbook link and responsible route. Do not include credentials, guest data or broadly exposed native addresses. Restricted links require their own authorization.

Route suspected cross-tenant access, credential compromise, unfenced writer or evidence tampering to security and the incident lead. Route availability/performance faults to SRE and the owning context; involve platform/service owners when their API/state is authoritative. Use [support responsibilities](support.md) and [alert handling](runbooks/handle-alert.md) to assign command and communications.

Deduplicate repeated symptoms into one incident while retaining each affected scope. Suppression is time-bounded, attributable and justified; maintenance may suppress expected availability noise but cannot suppress unexpected authority violations. Alert closure requires an observed recovery condition, not only an acknowledgement.

## Dashboards and SLO accounting

Provide an operator view of user journeys, dependency health/freshness, qualified scope, held/unknown jobs, queue/backlog age, reservation/evidence budgets and current incidents. Provide service-owner views of latency/error distribution, saturation, native API budgets and upgrade/recovery impact. Tenant views expose only authorized work and dependencies.

For each SLI define numerator/denominator or latency population, measurement source, evaluation window, exclusions and missing-data treatment. Count unavailable mandatory dependencies against the appropriate end-to-end journey, rather than reporting success from healthy process probes. Keep deliberate authorization denials distinguishable from unexpected service failures without hiding a fault that incorrectly denies valid work.

Discovery age, job completion duration and cutover outage are different measures; do not collapse them into API uptime. Control-plane recovery objectives and application data-loss/outage objectives also remain separate.

## Collection failure and validation

The P01 Compose/Kubernetes campaigns now implement [baseline resource observations](../implementation/p01-resource-observation.md)
at healthy and recovery checkpoints, retaining effective kernel limits and
explicit unlimited settings. Their synthetic measurements supply evidence for
resource review; they do not establish production sizing or accepted objectives.

Configure bounded local buffering/backpressure and a reviewed mandatory-audit policy. A disconnected worker may retain permitted observations, but buffer space does not extend authority lifetime. Lost mandatory evidence holds the dependent outcome; telemetry failure must not silently discard required accountability or trigger unreviewed replay.

Exercise one correlated operator journey through actual deployed services and an operation attempt. Inspect redaction at every sink, tenant-reader denial, alert delivery and acknowledgement, recovery notification, missing-telemetry detection and collector/backlog exhaustion. Record observed routing times, exact revisions and limits. Repeat affected checks when identity, exporters, retention, routes or signal semantics change.
