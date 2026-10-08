# Support and incident ownership

Accountable owner: service owner. Contributors: SRE, security, context owners, platform/shared-service owners and application owners. Scope: R29–R35; P00.05, P01.06, P10.04 and P11. The [support matrix](../implementation/support-matrix.md) defines intended combinations; actual support requires current qualification and operating acceptance.

## Service boundary

Support covers the accepted control-plane release, its configured dependencies and expressly published platform/operation/method/guest tuples. Application data correctness, native platform capacity, identity and shared-service availability require named owner interfaces. The portable hosting team coordinates these interfaces; a platform or application owner's responsibility does not disappear because a workflow invokes its API.

Before an environment enters service, record actual support hours, acknowledgement/update/escalation targets, primary and backup contacts, incident/change systems, maintenance windows, vendor entitlements and out-of-hours authority in its restricted service record. This document specifies responsibilities without inventing staffed coverage or accepted response times.

## Responsibilities

| Role | Accountable actions | Required handoff |
| --- | --- | --- |
| Service owner | Defines accepted scope/targets, funds coverage, accepts operational risk and communicates material service impact | Current service record, release/support limits and unresolved-risk owner |
| Service desk / first responder | Verifies request identity, gathers safe context, checks known incidents and routes without native writes | Tenant/environment, time, symptoms, correlation references and user impact |
| SRE incident lead | Coordinates containment, runtime/dependency diagnosis, recovery order and incident timeline | Explicit operational lead, decision log and next update owner |
| Owning context engineer | Diagnoses API/data/workflow semantics, prepares fixes and assesses compatibility | Affected contract/artifact/configuration and meaningful verification |
| Platform/shared-service owner | Confirms native outcomes, scoped credentials, capacity, service receipts and effective fencing | Independent native observation and permitted corrective action |
| IAM/security | Contains compromised identity, assesses data exposure and reviews trust/evidence risks | Scope, revocation/fencing observations and recovery trust decision |
| Application/data owner | Validates business service/data, chooses authorized divergence recovery and accepts outage/data result | Dataset/consistency checks, writer state and accepted recovery plan |
| Assurance/release owner | Assesses claim revocation/retest, evidence custody and release requalification | Exact affected tuple/artifacts and support publication decision |

Operators must have enough read authority to diagnose their assigned scope. Privileged support actions use [identity and trust](identity-and-trust.md) controls; support membership alone does not permit approval, secret retrieval, target deletion or data disposal.

## Incident classification

| Class | Examples and initial priority basis | Initial control |
| --- | --- | --- |
| Safety/security incident | Suspected cross-tenant access, compromised signer, active duplicate writer, possible data loss | Preserve evidence and immediately contain affected authority/data path; security and application owners join |
| Service unavailable | Valid users cannot complete accepted journeys; required dependency unavailable | Assess all affected tenants/sites, hold unsafe new admission, activate service record's response target |
| Degraded or held work | Growing queue, stale discovery, evidence/reservation failure, unknown native operation | Keep holds; prioritize according to impending safe-budget expiry and application impact |
| Service request / change | New tenant/site/tuple, capacity increase or supported configuration change | Follow scoped change and qualification process; do not treat request as incident permission |

The incident lead assigns the organization's severity using observed impact and urgency. A working console does not reduce the severity of uncontained writes or lost application data. An unsupported tuple request becomes a capability request; it must not acquire support through an incident workaround.

## Triage and escalation

1. Verify reporter identity/scope and capture environment, release/configuration, tenant/job/operation IDs, last known good state and times. Gather read-only observations without copying secrets or workload payloads.
2. Check [observability](observability.md), current incidents and underlying authority/dependency health. Distinguish missing evidence from confirmed failure.
3. Identify the authoritative owner for each disputed fact. Native state comes from scoped independent platform observations; approval from governance; intent from catalogue; support from assurance.
4. Apply the narrowest effective containment, record affected running work and verify it. Cancellation requests do not prove a native call stopped; uncertain operations remain held.
5. Escalate before authority, staging, retention or outage budgets expire. Assign one incident lead and explicit action owners; follow [alert handling](runbooks/handle-alert.md).
6. Use the relevant approved runbook/recovery action. Record expected state, actual observation and next decision before continuing; never manually change a database row to manufacture success.

If a native endpoint cannot be observed or fenced, retain the hold and escalate to its owner. If target writes exist, the application owner participates in forward/source-return recovery; restarting the old source is not a generic availability fix.

## Communications and closure

The incident lead names a communications owner and audience appropriate to affected tenants and classification. Updates state verified impact, containment, current uncertainty, next action and next update time from the service record. Route external/vendor disclosures through approved support agreements and redact unrelated tenant information.

Close the incident only after independently validating the affected user journey, durable/native/data state, restored alerting and current authority. Record any residual holds or reduced support scope, actual outage/recovery times, evidence references and owner acknowledgement. A workaround with unresolved risk remains explicitly bounded.

Perform a review for material incidents: causal sequence, detection gaps, controls that worked or failed, affected qualification, corrective packages and owners/dates. Preserve original evidence and append findings; do not rewrite history to match the recovered state.

## Operational handover

The receiving team needs the exact installed BOM, accepted support tuple, operating targets, alert routes, access/trust/recovery dependencies, retention/key custody, maintenance procedure and rehearsed install/restore/upgrade evidence. An operator other than the author must demonstrate required tasks and escalation delivery. [Runbooks](runbooks/README.md) provide the task catalogue; missing required exercise evidence keeps the corresponding acceptance gate open.
